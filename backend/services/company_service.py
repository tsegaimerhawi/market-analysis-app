"""Fetch stock data and company info using yfinance."""
import pandas as pd
from utils.logger import logger


def get_history(symbol, start_date=None, end_date=None):
    """
    Fetch OHLCV history for a symbol. Returns DataFrame with DatetimeIndex and Close (and Open, High, Low, Volume).
    Same format as load_data from CSV for algorithm compatibility.
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    try:
        import yfinance as yf
    except ImportError:
        logger.debug("yfinance not installed")
        return None
    try:
        # Strip time if present to prevent yfinance ValueError: unconverted data remains
        if start_date and len(start_date) > 10:
            start_date = start_date[:10]
        if end_date and len(end_date) > 10:
            end_date = end_date[:10]

        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, auto_adjust=True)
        if df is None or df.empty or len(df) < 10:
            return None
        df.index = pd.to_datetime(df.index)
        df.index.name = "Date"
        df.sort_index(inplace=True)
        # Ensure required columns
        if "Close" not in df.columns:
            return None
        return df[["Open", "High", "Low", "Close", "Volume"]].copy() if all(c in df.columns for c in ["Open", "High", "Low", "Volume"]) else df[["Close"]].copy()
    except Exception as e:
        logger.exception("yfinance get_history failed: %s", e)
        return None


def get_info(symbol):
    """
    Fetch full company info from yfinance (everything available).
    Returns a dict suitable for JSON (scalars only; nested objects simplified).
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed"}
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info:
            return {"symbol": symbol, "error": "No info returned"}
        # Flatten/serialize for JSON: keep scalars, convert lists/dicts to strings or first level
        out = {}
        for k, v in info.items():
            if v is None:
                out[k] = None
            elif isinstance(v, (str, int, float, bool)):
                out[k] = v
            elif isinstance(v, (list, tuple)):
                out[k] = [x if isinstance(x, (str, int, float, bool)) else str(x) for x in v[:50]]
            elif isinstance(v, dict):
                out[k] = {str(a): (b if isinstance(b, (str, int, float, bool)) else str(b)) for a, b in list(v.items())[:20]}
            else:
                out[k] = str(v)
        return out
    except Exception as e:
        logger.exception("yfinance get_info failed: %s", e)
        return {"symbol": symbol, "error": str(e)}


def search(query):
    """
    Search for tickers by name/symbol. Uses yfinance tickers list or fallback.
    Returns list of {symbol, shortName/longName} for display.
    """
    query = (query or "").strip()
    if not query or len(query) < 1:
        return []
    try:
        import yfinance as yf
        # yfinance doesn't have a real search API; we can use ticker.info for a single symbol
        # For search, use pandas_datareader or a simple mapping. Alternatively use yf.Ticker(query).info to validate.
        ticker = yf.Ticker(query.upper())
        info = ticker.info
        if info and info.get("symbol"):
            return [{"symbol": info.get("symbol", query.upper()), "name": info.get("shortName") or info.get("longName") or info.get("symbol", "")}]
        return []
    except Exception:
        return []
