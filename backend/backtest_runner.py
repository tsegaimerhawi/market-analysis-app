"""
Backtest the trading ensemble on historical data.
Simulates running the orchestrator each day; computes Sharpe, max drawdown, win rate.
"""
import math
from datetime import datetime, timedelta
from typing import List, Optional

from agents.llm_manager import LLMManager
from agents.lstm_predictor import LSTMPredictor
from agents.technical_analyst import TechnicalAnalyst
from agents.trade_orchestrator import TradeOrchestrator
from agents.xgboost_analyst import XGBoostAnalyst
from services.company_service import get_history
from services.macro_fetcher import get_macro_indicators
from services.news_fetcher import get_headlines

LOOKBACK_MIN = 35
INITIAL_CASH = 10_000.0


def _volatility_from_closes(closes: List[float]) -> Optional[float]:
    if not closes or len(closes) < 2:
        return None
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] and closes[i - 1] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
    if len(returns) < 2:
        return None
    mean_ret = sum(returns) / len(returns)
    var = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    return (var * 252) ** 0.5


def run_backtest(symbol: str, days: int = 90, full_control: bool = False) -> dict:
    """
    Run ensemble backtest on symbol. Returns dict with:
    total_return_pct, sharpe_ratio, max_drawdown_pct, win_rate_pct, num_trades, equity_curve (last 20).
    When full_control=True, orchestrator uses full-control path (no guardrails, direct composite).
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return {"error": "Symbol required"}
    end = datetime.utcnow()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    df = get_history(symbol, start, end_str)
    if df is None or df.empty or "Close" not in df.columns:
        return {"error": f"Insufficient history for {symbol}"}
    closes = df["Close"].tolist()
    if len(closes) < LOOKBACK_MIN + 5:
        return {"error": f"Need at least {LOOKBACK_MIN + 5} days of data"}

    orchestrator = TradeOrchestrator(
        lstm=LSTMPredictor(),
        xgb=XGBoostAnalyst(),
        technical=TechnicalAnalyst(),
        llm=LLMManager(),
    )
    cash = INITIAL_CASH
    position = 0.0
    cost_basis = 0.0
    equity_curve = [INITIAL_CASH]
    trade_pnls = []

    for i in range(LOOKBACK_MIN, len(closes) - 1):
        # The current 'simulated' date
        sim_date = df.index[i]
        
        history_closes = closes[: i + 1]
        current_price = closes[i]
        next_price = closes[i + 1]
        vol = _volatility_from_closes(history_closes[-60:]) if len(history_closes) >= 60 else None
        
        # Pass sim_date to prevent look-ahead bias
        headlines = get_headlines(symbol, as_of_date=sim_date)
        macro = get_macro_indicators(as_of_date=sim_date)
        
        decision = orchestrator.decide(
            symbol=symbol,
            history_closes=history_closes,
            headlines=headlines,
            macro_indicators=macro,
            current_price=current_price,
            volatility_annual=vol,
            bid_ask_spread_pct=None,
            full_control=full_control,
        )
        if decision.action == "Buy" and cash > 0 and decision.position_size > 0:
            amount = cash * decision.position_size
            qty = amount / current_price if current_price else 0
            if qty > 0:
                cost_basis = (cost_basis * position + amount) / (position + qty) if (position + qty) else current_price
                position += qty
                cash -= amount
        elif decision.action == "Sell" and position > 0 and decision.position_size > 0:
            sell_qty = position * decision.position_size
            if sell_qty > 0:
                proceeds = sell_qty * current_price
                pnl = (current_price - cost_basis) * sell_qty
                trade_pnls.append(pnl)
                cash += proceeds
                position -= sell_qty
                if position < 1e-9:
                    position = 0
                    cost_basis = 0

        mark_to_market = cash + position * next_price if next_price else cash
        equity_curve.append(mark_to_market)

    final_equity = equity_curve[-1] if equity_curve else INITIAL_CASH
    total_return_pct = (final_equity - INITIAL_CASH) / INITIAL_CASH * 100

    returns = []
    for j in range(1, len(equity_curve)):
        if equity_curve[j - 1] and equity_curve[j - 1] > 0:
            returns.append((equity_curve[j] - equity_curve[j - 1]) / equity_curve[j - 1])
    sharpe_ratio = 0.0
    if len(returns) >= 2:
        mean_r = sum(returns) / len(returns)
        std_r = (sum((r - mean_r) ** 2 for r in returns) / len(returns)) ** 0.5
        if std_r and std_r > 0:
            sharpe_ratio = (mean_r / std_r) * math.sqrt(252)

    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak else 0
        if dd > max_dd:
            max_dd = dd

    wins = sum(1 for p in trade_pnls if p > 0)
    win_rate_pct = (wins / len(trade_pnls) * 100) if trade_pnls else 0

    return {
        "symbol": symbol,
        "days": days,
        "full_control": full_control,
        "initial_cash": INITIAL_CASH,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "win_rate_pct": round(win_rate_pct, 1),
        "num_trades": len(trade_pnls),
        "equity_curve_tail": [round(x, 2) for x in equity_curve[-20:]],
    }
