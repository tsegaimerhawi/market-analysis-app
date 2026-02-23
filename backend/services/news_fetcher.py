"""
Fetch real news headlines for a symbol when NEWS_API_KEY (NewsAPI.org) is set.
Otherwise return stub for Sentiment agent.
"""

import os
from typing import List

from utils.logger import logger

NEWS_API_KEY = (os.environ.get("NEWS_API_KEY") or os.environ.get("NEWSAPI_KEY") or "").strip()
NEWS_API_URL = "https://newsapi.org/v2/everything"


def get_headlines(symbol: str, max_items: int = 15, as_of_date=None) -> List[str]:
    """
    Return list of headline strings for the symbol.
    If NEWS_API_KEY is set, fetch from NewsAPI.org; else return stub.
    """
    if not symbol or not (symbol := (symbol or "").strip().upper()):
        return ["No symbol provided."]
    if not NEWS_API_KEY:
        return [f"Market update for {symbol} (set NEWS_API_KEY for real headlines)."]
    try:
        from datetime import datetime, timedelta

        import httpx

        # Use as_of_date (if provided) to avoid look-ahead bias during backtests
        if as_of_date is None:
            to_date = datetime.utcnow()
        else:
            as_of_str = str(as_of_date).replace("Z", "")
            to_date = (
                as_of_date
                if isinstance(as_of_date, datetime)
                else datetime.fromisoformat(as_of_str)
            )

        from_date = (to_date - timedelta(days=2)).strftime("%Y-%m-%d")
        to_date_str = to_date.strftime("%Y-%m-%d")

        params = {
            "q": symbol,
            "from": from_date,
            "to": to_date_str,
            "sortBy": "publishedAt",
            "pageSize": min(max_items, 20),
            "apiKey": NEWS_API_KEY,
            "language": "en",
        }
        with httpx.Client(timeout=10.0) as client:
            r = client.get(NEWS_API_URL, params=params)
        if not r.is_success:
            logger.debug("NewsAPI failed %s: %s", r.status_code, r.text[:200])
            return [f"Market update for {symbol} (news fetch failed)."]
        data = r.json()
        articles = data.get("articles") or []
        headlines = []
        for a in articles[:max_items]:
            title = (a.get("title") or "").strip()
            if title:
                headlines.append(title)
        if not headlines:
            return [f"No recent headlines for {symbol}."]
        return headlines
    except Exception as e:
        logger.debug("news_fetcher get_headlines %s: %s", symbol, e)
        return [f"Market update for {symbol} (error: {e})."]
