"""
Single-cycle runner for the trading agent. Called when agent is enabled (e.g. by a scheduler or thread).
Gathers data for each symbol (watchlist + optional volatile list), runs TradeOrchestrator, logs reasoning, and executes paper trades.
When Volatile is on: default stop-loss applies if none set; position size is capped for volatile-only symbols to limit risk.
"""
import json
import sys
import os

# Safeguards when volatile stocks are enabled
DEFAULT_STOP_LOSS_PCT_WHEN_VOLATILE = 5.0   # use this if user didn't set stop-loss (limit losses)
MAX_POSITION_SIZE_VOLATILE_ONLY = 0.15      # max 15% of cash per buy for symbols from volatile list only (not watchlist)

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import (
    get_watchlist,
    get_cash_balance,
    get_positions,
    get_position,
    execute_buy,
    execute_sell,
    add_agent_reasoning,
    add_agent_history,
    get_agent_enabled,
    get_agent_include_volatile,
    get_agent_stop_loss_pct,
    get_agent_take_profit_pct,
    get_agent_full_control,
    set_last_agent_history_executed,
    get_orders,
)
from services.company_service import get_history, get_quote
from services.volatility_scanner import get_volatile_symbols, get_candidate_symbols_from_file, get_normal_symbols_from_file
from services.telegram_notify import send_message as send_telegram_message
from services.news_fetcher import get_headlines
from services.macro_fetcher import get_macro_indicators
from agents.trade_orchestrator import TradeOrchestrator
from agents.llm_manager import LLMManager
from agents.lstm_predictor import LSTMPredictor
from agents.xgboost_analyst import XGBoostAnalyst
from utils.logger import logger


def _reasoning_callback(symbol: str, step: str, message: str, data: dict):
    add_agent_reasoning(symbol, step, message, data)


def _get_closes(symbol: str, days: int = 60):
    """Fetch recent close prices for a symbol."""
    from datetime import datetime, timedelta
    end = datetime.utcnow()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    df = get_history(symbol, start, end_str)
    if df is None or df.empty or "Close" not in df.columns:
        return None
    return df["Close"].tolist()


def _volatility_from_closes(closes):
    """Annualized volatility approximation from daily closes (log returns)."""
    if not closes or len(closes) < 2:
        return None
    import math
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] and closes[i - 1] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
    if not returns:
        return None
    mean_ret = sum(returns) / len(returns)
    var = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    return (var * 252) ** 0.5  # annualized


def _get_volatile_symbols_dynamic():
    """Compute volatile symbols from 8h market data (algorithm + small-cap bias). Uses candidates from volatile_symbols.json."""
    candidates = get_candidate_symbols_from_file()
    if not candidates:
        return []
    return get_volatile_symbols(candidates, top_n=25)


def run_agent_cycle():
    """
    Run one full cycle: for each symbol (watchlist + normal list + optional volatile list), run orchestrator, log reasoning, execute if Buy/Sell.
    """
    if not get_agent_enabled():
        logger.debug("Agent cycle skipped: agent is disabled")
        return

    watchlist = get_watchlist()
    watchlist_symbols = {(item.get("symbol") or "").strip().upper() for item in watchlist if (item.get("symbol") or "").strip()}
    normal_symbols = set(get_normal_symbols_from_file())

    # Base universe: watchlist + normal list (normal_symbols.json). When volatile is off, agent uses only this.
    symbols_to_run = list(watchlist_symbols)
    for s in normal_symbols:
        if s and s not in watchlist_symbols:
            symbols_to_run.append(s)

    # When both auto-trading and Volatile stocks are on: add volatile list (top 25 from volatile_symbols.json).
    # Otherwise we use only the normal list (+ watchlist) above.
    volatile_only_symbols = set()
    if get_agent_include_volatile():
        volatile = _get_volatile_symbols_dynamic()
        already = set(symbols_to_run)
        extra = [s for s in volatile if s and s not in already]
        volatile_only_symbols = set(extra)
        symbols_to_run = symbols_to_run + extra
        if extra:
            add_agent_reasoning("VOLATILE", "volatile", f"Added {len(extra)} volatile symbols (8h algo + small-cap bias): {', '.join(extra[:10])}{'...' if len(extra) > 10 else ''}", {"count": len(extra), "symbols": extra})

    # Always include symbols we currently hold: run ensemble on them to decide sell/hold (e.g. volatile names no longer in top list).
    positions = get_positions()
    for pos in positions:
        sym = (pos.get("symbol") or "").strip().upper()
        if sym and sym not in set(symbols_to_run):
            symbols_to_run.append(sym)

    if not symbols_to_run:
        logger.warning(
            "Agent cycle skipped: no symbols to run (watchlist and normal_symbols.json empty or missing). "
            "Add symbols in the app Watchlist or Normal Symbols page."
        )
        return

    full_control = get_agent_full_control()
    logger.info(
        "Agent cycle starting | symbols=%s | full_control=%s | volatile_included=%s",
        len(symbols_to_run),
        full_control,
        get_agent_include_volatile(),
    )
    cycle_updates = []  # collect buy/sell/stop-loss/take-profit for Telegram

    llm = LLMManager()
    orchestrator = TradeOrchestrator(
        lstm=LSTMPredictor(),
        xgb=XGBoostAnalyst(),
        llm=llm,
        on_reasoning=_reasoning_callback,
    )

    stop_loss_pct = get_agent_stop_loss_pct()
    take_profit_pct = get_agent_take_profit_pct()
    # When volatile is on and not full_control, enforce a default stop-loss if user didn't set one (limit losses)
    if not full_control and get_agent_include_volatile() and stop_loss_pct is None:
        stop_loss_pct = DEFAULT_STOP_LOSS_PCT_WHEN_VOLATILE
        add_agent_reasoning("VOLATILE", "guardrail", f"Volatile on: using default stop-loss {stop_loss_pct}% (set your own in Control to override)", {"default_stop_loss_pct": stop_loss_pct})

    # Fetch cash once at the start of the cycle to avoid 'cascade' buying where earlier symbols
    # get larger absolute positions than later symbols due to diminishing cash balance.
    cycle_start_cash = get_cash_balance()
    deployed_this_cycle = 0.0

    for symbol in symbols_to_run:
        if not symbol:
            continue
        try:
            quote = get_quote(symbol)
            current_price = quote.get("price") if quote else None
            position = get_position(symbol)
            pos_qty = float(position["quantity"]) if position else 0
            avg_cost = float(position["avg_cost"]) if position else None

            # --- Stop-loss / Take-profit (skipped when full_control; only agent decides sells) ---
            # (No changes here, kept for context)
            if not full_control and position and current_price and avg_cost and avg_cost > 0 and pos_qty > 0:
                pnl_pct = (current_price - avg_cost) / avg_cost * 100
                if stop_loss_pct is not None and pnl_pct <= -stop_loss_pct:
                    ok, _, _ = execute_sell(symbol, pos_qty, current_price)
                    order_id = None
                    if ok:
                        recent = get_orders(limit=1)
                        order_id = recent[0]["id"] if recent else None
                    add_agent_history(symbol, "Sell", 1.0, f"Stop-loss: P&L {pnl_pct:.1f}% <= -{stop_loss_pct}%", executed=ok, order_id=order_id, guardrail_triggered=True)
                    add_agent_reasoning(symbol, "stop_loss", f"Stop-loss triggered: P&L {pnl_pct:.1f}% <= -{stop_loss_pct}%, sold full position", {"pnl_pct": pnl_pct})
                    cycle_updates.append(f"🛑 SELL {symbol} (stop-loss) P&L {pnl_pct:.1f}%")
                    continue
                if take_profit_pct is not None and pnl_pct >= take_profit_pct:
                    ok, _, _ = execute_sell(symbol, pos_qty, current_price)
                    order_id = None
                    if ok:
                        recent = get_orders(limit=1)
                        order_id = recent[0]["id"] if recent else None
                    add_agent_history(symbol, "Sell", 1.0, f"Take-profit: P&L {pnl_pct:.1f}% >= {take_profit_pct}%", executed=ok, order_id=order_id, guardrail_triggered=True)
                    add_agent_reasoning(symbol, "take_profit", f"Take-profit triggered: P&L {pnl_pct:.1f}% >= {take_profit_pct}%, sold full position", {"pnl_pct": pnl_pct})
                    cycle_updates.append(f"✅ SELL {symbol} (take-profit) P&L {pnl_pct:.1f}%")
                    continue

            closes = _get_closes(symbol)
            volatility = _volatility_from_closes(closes) if closes else None
            headlines = get_headlines(symbol)
            macro_indicators = get_macro_indicators()

            decision = orchestrator.decide(
                symbol=symbol,
                history_closes=closes,
                headlines=headlines,
                macro_indicators=macro_indicators,
                current_price=current_price,
                volatility_annual=volatility,
                bid_ask_spread_pct=None,
                full_control=full_control,
            )

            # Log decision to history (before execution)
            add_agent_history(
                symbol=symbol,
                action=decision.action,
                position_size=decision.position_size,
                reason=decision.reason,
                executed=False,
                order_id=None,
                guardrail_triggered=decision.guardrail_triggered,
            )

            if decision.action == "Hold" or decision.position_size <= 0:
                continue

            if not quote or current_price is None or current_price <= 0:
                add_agent_reasoning(symbol, "execute", "Skipped: no quote/price", {})
                continue

            # Cap position size for volatile-only symbols when not full_control (full_control uses orchestrator size as-is)
            position_size = decision.position_size
            if not full_control and symbol in volatile_only_symbols and position_size > MAX_POSITION_SIZE_VOLATILE_ONLY:
                position_size = MAX_POSITION_SIZE_VOLATILE_ONLY
                add_agent_reasoning(symbol, "guardrail", f"Volatile-only symbol: position size capped to {MAX_POSITION_SIZE_VOLATILE_ONLY:.0%} of cash", {"capped": True})

            if decision.action == "Buy":
                # Position size as fraction of cycle-start cash to deploy
                amount = cycle_start_cash * position_size
                current_cash = get_cash_balance()
                
                # Check if we still have enough physical cash to execute the planned amount
                actual_spend = min(amount, current_cash)
                quantity = actual_spend / current_price if current_price else 0
                
                if quantity > 0 and actual_spend > 0:
                    ok, _, _ = execute_buy(symbol, quantity, current_price)
                    if ok:
                        deployed_this_cycle += actual_spend
                        recent = get_orders(limit=1)
                        order_id = recent[0]["id"] if recent else None
                        add_agent_reasoning(symbol, "execute", f"Executed buy {quantity:.4f} @ {current_price}", {"order_id": order_id})
                        cycle_updates.append(f"📈 BUY {symbol} {quantity:.2f} @ ${current_price:.2f}")
                    else:
                        add_agent_reasoning(symbol, "execute", "Buy failed (check cash balance)", {})
            elif decision.action == "Sell" and pos_qty > 0:
                # Sell fraction of position
                sell_qty = pos_qty * decision.position_size
                if sell_qty > 0:
                    ok, _, _ = execute_sell(symbol, sell_qty, current_price)
                    if ok:
                        recent = get_orders(limit=1)
                        order_id = recent[0]["id"] if recent else None
                        add_agent_reasoning(symbol, "execute", f"Executed sell {sell_qty:.4f} @ {current_price}", {"order_id": order_id})
                        cycle_updates.append(f"📉 SELL {symbol} {sell_qty:.2f} @ ${current_price:.2f}")
                    else:
                        add_agent_reasoning(symbol, "execute", "Sell failed", {})

            if order_id is not None:
                set_last_agent_history_executed(symbol, order_id)
        except Exception as e:
            logger.exception("Agent cycle error for %s: %s", symbol, e)
            add_agent_reasoning(symbol, "error", str(e), {})

    from datetime import datetime
    header = f"🤖 Trading Agent — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
    if cycle_updates:
        body = "\n".join(cycle_updates)
        msg = header + body
    else:
        msg = header + "No trades this cycle (all Hold or no signals). Agent is running.\n"

    # Append portfolio summary: cash, positions value, total
    cash = get_cash_balance()
    positions = get_positions()
    positions_value = 0.0
    position_lines = []
    for pos in positions:
        sym = (pos.get("symbol") or "").strip().upper()
        qty = float(pos.get("quantity") or 0)
        quote = get_quote(sym) if sym else None
        price = float(quote.get("price")) if quote and quote.get("price") is not None else float(pos.get("avg_cost") or 0)
        val = qty * price
        positions_value += val
        position_lines.append(f"  {sym}: {qty:.2f} @ ${price:.2f} = ${val:.2f}")
    total = cash + positions_value
    msg += "\n📊 Portfolio\n"
    msg += f"  Cash: ${cash:,.2f}\n"
    msg += f"  Positions: ${positions_value:,.2f}\n"
    if position_lines:
        msg += "\n".join(position_lines) + "\n"
    msg += f"  Total: ${total:,.2f}"
    ok, err = send_telegram_message(msg)
    if not ok and err:
        logger.warning("Telegram notify failed: %s", err)
    logger.info("Agent cycle finished | trades_this_cycle=%s", len(cycle_updates))
