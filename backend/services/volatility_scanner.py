"""
Volatility scanner: identifies volatile stocks from recent market data (e.g. last ~8 hours).
Biases toward smaller / startup-like companies (lower market cap = more volatile in practice).
Used when "Volatile stocks" is on so the agent can buy/sell these names with stop-loss/take-profit.
"""
import json
import math
import os
from typing import List, Optional, Tuple

from utils.logger import logger

# Max market cap (USD) to count as "small/startup-like" for extra volatility weight. Above this we still rank by vol only.
SMALL_CAP_CUTOFF = 50_000_000_000  # 50B
# How many hours of bars to use for volatility (approximate trading hours in one day)
HOURS_LOOKBACK = 8
# Min number of price bars required to compute volatility
MIN_BARS = 4
# Symbols to always include in the volatile list when they're in candidates and have valid data (e.g. high-interest names)
ALWAYS_INCLUDE_IN_VOLATILE = ["GME", "AMC"]


def _get_intraday_closes(symbol: str, interval: str = "1h", period: str = "5d") -> Optional[List[float]]:
    """
    Fetch recent intraday close prices. Uses ~8 hours of data when available (last 8 bars of 1h).
    Falls back to daily data (last 5 days) if intraday is unavailable (e.g. outside market hours).
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty or "Close" not in df.columns:
            # Fallback: daily data for last 5 days (still gives volatility ranking)
            df = ticker.history(period="5d", interval="1d", auto_adjust=True)
            if df is None or df.empty or "Close" not in df.columns or len(df) < MIN_BARS:
                return None
        df = df.sort_index()
        closes = df["Close"].dropna().tolist()
        n_bars = min(HOURS_LOOKBACK, len(closes))
        if n_bars < MIN_BARS:
            return None
        return closes[-n_bars:]
    except Exception as e:
        logger.debug("volatility_scanner intraday %s: %s", symbol, e)
        return None


def _volatility_from_closes(closes: List[float]) -> Optional[float]:
    """Return annualized volatility (std of log returns * sqrt(252*6.5) for hourly)."""
    if not closes or len(closes) < MIN_BARS:
        return None
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] and closes[i - 1] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
    if len(returns) < 2:
        return None
    mean_ret = sum(returns) / len(returns)
    var = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    # Scale to annualized: ~252*6.5 trading hours per year
    return math.sqrt(var * 252 * 6.5)


def _get_market_cap(symbol: str) -> Optional[float]:
    """Return market cap in USD from yfinance info, or None."""
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        cap = info.get("marketCap") or info.get("enterpriseValue")
        if cap is not None:
            return float(cap)
        return None
    except Exception:
        return None


def compute_volatility_score(symbol: str) -> Optional[Tuple[float, Optional[float]]]:
    """
    Compute volatility score for one symbol from recent intraday data.
    Returns (volatility_score, market_cap) or None if insufficient data.
    Higher score = more volatile. Small-cap gets a boost.
    """
    closes = _get_intraday_closes(symbol)
    if not closes:
        return None
    vol = _volatility_from_closes(closes)
    if vol is None:
        return None
    cap = _get_market_cap(symbol)
    # Boost score for small/startup-like (lower market cap)
    if cap is not None and cap < SMALL_CAP_CUTOFF:
        # Smaller cap → higher multiplier (e.g. 1.0 to 1.5)
        size_factor = 1.0 + 0.5 * (1.0 - min(1.0, cap / SMALL_CAP_CUTOFF))
        vol = vol * size_factor
    return (vol, cap)


def get_volatile_symbols(
    candidate_symbols: List[str],
    top_n: int = 25,
    min_volatility: float = 0.0,
) -> List[str]:
    """
    Rank candidates by 8-hour volatility (with small-cap bias) and return top N.
    Symbols in ALWAYS_INCLUDE_IN_VOLATILE (e.g. GME, AMC) are included first when they have valid data.
    candidate_symbols: list of tickers to scan (e.g. from volatile_symbols.json).
    """
    candidates_set = {(s or "").strip().upper() for s in candidate_symbols if (s or "").strip()}
    always = [s for s in ALWAYS_INCLUDE_IN_VOLATILE if (s or "").strip().upper() in candidates_set]
    results = []
    for sym in candidate_symbols:
        sym = (sym or "").strip().upper()
        if not sym:
            continue
        try:
            score_cap = compute_volatility_score(sym)
            if score_cap is not None:
                vol_score, _ = score_cap
                if vol_score >= min_volatility:
                    results.append((sym, vol_score))
        except Exception as e:
            logger.debug("volatility_scanner skip %s: %s", sym, e)
    results.sort(key=lambda x: x[1], reverse=True)
    # Build list: always-include first (if they have data), then fill with top by score
    ordered = []
    seen = set()
    for s in always:
        for sym, score in results:
            if sym == s and sym not in seen:
                ordered.append(sym)
                seen.add(sym)
                break
    for sym, _ in results:
        if len(ordered) >= top_n:
            break
        if sym not in seen:
            ordered.append(sym)
            seen.add(sym)
    return ordered[:top_n]


def get_volatile_symbols_with_scores(
    candidate_symbols: List[str],
    top_n: int = 25,
) -> List[dict]:
    """Like get_volatile_symbols but returns list of {symbol, volatility_score, market_cap}."""
    results = []
    for sym in candidate_symbols:
        sym = (sym or "").strip().upper()
        if not sym:
            continue
        try:
            score_cap = compute_volatility_score(sym)
            if score_cap is not None:
                vol_score, cap = score_cap
                results.append({"symbol": sym, "volatility_score": round(vol_score, 4), "market_cap": cap})
        except Exception:
            continue
    results.sort(key=lambda x: x["volatility_score"], reverse=True)
    return results[:top_n]


def get_candidate_symbols_from_file() -> List[str]:
    """Load candidate symbols from data/volatile_symbols.json (universe to scan)."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "volatile_symbols.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [str(s).strip().upper() for s in data if s]
    except Exception:
        return []


def get_normal_symbols_from_file() -> List[str]:
    """Load normal/stable stock symbols from data/normal_symbols.json (e.g. AAPL, NVDA, AMZN, META)."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "normal_symbols.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [str(s).strip().upper() for s in data if s]
    except Exception:
        return []
