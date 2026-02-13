"""
Single-cycle runner for the trading agent. Called when agent is enabled (e.g. by a scheduler or thread).
Gathers data for each watchlist symbol, runs TradeOrchestrator, logs reasoning, and executes paper trades.
"""
import sys
import os

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
)
from services.company_service import get_history, get_quote
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


def run_agent_cycle():
    """
    Run one full cycle: for each watchlist symbol, run orchestrator, log reasoning, execute if Buy/Sell.
    """
    if not get_agent_enabled():
        return

    watchlist = get_watchlist()
    if not watchlist:
        logger.debug("Agent cycle: no watchlist symbols")
        return

    llm = LLMManager()
    orchestrator = TradeOrchestrator(
        lstm=LSTMPredictor(),
        xgb=XGBoostAnalyst(),
        llm=llm,
        on_reasoning=_reasoning_callback,
    )

    for item in watchlist:
        symbol = (item.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        try:
            closes = _get_closes(symbol)
            quote = get_quote(symbol)
            current_price = quote.get("price") if quote else None
            volatility = _volatility_from_closes(closes) if closes else None
            # Stub headlines and macro (in production, plug in news API and macro data)
            headlines = [f"Market update for {symbol}"]
            macro_indicators = {"description": "CPI and rates stable; no major macro update."}

            decision = orchestrator.decide(
                symbol=symbol,
                history_closes=closes,
                headlines=headlines,
                macro_indicators=macro_indicators,
                current_price=current_price,
                volatility_annual=volatility,
                bid_ask_spread_pct=None,
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

            cash = get_cash_balance()
            position = get_position(symbol)
            pos_qty = float(position["quantity"]) if position else 0

            order_id = None
            if decision.action == "Buy":
                # Position size as fraction of cash to deploy
                amount = cash * decision.position_size
                quantity = amount / current_price if current_price else 0
                if quantity > 0 and amount <= cash:
                    ok, _, _ = execute_buy(symbol, quantity, current_price)
                    if ok:
                        from db import get_orders
                        recent = get_orders(limit=1)
                        order_id = recent[0]["id"] if recent else None
                        add_agent_reasoning(symbol, "execute", f"Executed buy {quantity:.4f} @ {current_price}", {"order_id": order_id})
                    else:
                        add_agent_reasoning(symbol, "execute", "Buy failed (e.g. insufficient cash)", {})
            elif decision.action == "Sell" and pos_qty > 0:
                # Sell fraction of position
                sell_qty = pos_qty * decision.position_size
                if sell_qty > 0:
                    ok, _, _ = execute_sell(symbol, sell_qty, current_price)
                    if ok:
                        from db import get_orders
                        recent = get_orders(limit=1)
                        order_id = recent[0]["id"] if recent else None
                        add_agent_reasoning(symbol, "execute", f"Executed sell {sell_qty:.4f} @ {current_price}", {"order_id": order_id})
                    else:
                        add_agent_reasoning(symbol, "execute", "Sell failed", {})

            # Update last history row to executed if we placed an order
            if order_id is not None:
                from db import set_last_agent_history_executed
                set_last_agent_history_executed(symbol, order_id)
        except Exception as e:
            logger.exception("Agent cycle error for %s: %s", symbol, e)
            add_agent_reasoning(symbol, "error", str(e), {})
