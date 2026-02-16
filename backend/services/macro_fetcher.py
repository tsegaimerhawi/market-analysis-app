"""
Fetch macro indicators (rates, CPI, etc.) when MACRO_API_KEY or similar is set.
Otherwise return stub description for Macro LLM agent.
"""
import os
from typing import Dict, Any
from utils.logger import logger

# Optional: set MACRO_API_KEY or use a free endpoint (e.g. FRED, Alpha Vantage) for rates/CPI
MACRO_API_KEY = (os.environ.get("MACRO_API_KEY") or os.environ.get("ALPHA_VANTAGE_API_KEY") or "").strip()


def get_macro_indicators() -> Dict[str, Any]:
    """
    Return dict with macro description and optional series for the Macro agent.
    If no API key, returns stub. Keys: description (str), optional rates, cpi, etc.
    """
    if not MACRO_API_KEY:
        return {"description": "CPI and rates stable; no major macro update. Set MACRO_API_KEY for real data."}
    try:
        # Example: Alpha Vantage has macroeconomic data; adapt URL/params as needed
        import httpx
        url = "https://www.alphavantage.co/query"
        params = {"function": "FEDERAL_FUNDS_RATE", "apikey": MACRO_API_KEY, "limit": "1"}
        with httpx.Client(timeout=8.0) as client:
            r = client.get(url, params=params)
        if not r.is_success:
            return {"description": "Macro data unavailable (API error)."}
        data = r.json()
        rates = data.get("data") or []
        if rates:
            latest = rates[0] if isinstance(rates[0], dict) else {}
            value = latest.get("value", "N/A")
            return {"description": f"Fed funds rate latest: {value}. CPI and employment to be added."}
        return {"description": "Macro data unavailable."}
    except Exception as e:
        logger.debug("macro_fetcher: %s", e)
        return {"description": f"Macro fetch error: {e}. Using stub."}
