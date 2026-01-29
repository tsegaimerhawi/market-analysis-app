"""Fetch articles from news sources (RSS feeds)."""
from datetime import datetime
from utils.logger import logger


def get_newspapers():
    """Load list of newspapers from data file."""
    import os
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "data", "newspapers.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def scrape_articles(newspaper_id, start_date=None, end_date=None):
    """
    Fetch articles from the given newspaper (RSS feed).
    start_date, end_date: YYYY-MM-DD strings or None.
    Returns list of {title, link, published, summary, source}.
    """
    newspapers = {n["id"]: n for n in get_newspapers()}
    if newspaper_id not in newspapers:
        return []
    source = newspapers[newspaper_id]
    feed_url = source.get("feed")
    if not feed_url:
        return []
    try:
        import feedparser
    except ImportError:
        logger.debug("feedparser not installed")
        return []

    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:50]:
            pub = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    from time import mktime
                    pub = datetime.fromtimestamp(mktime(entry.published_parsed))
                except Exception:
                    pass
            if not pub and getattr(entry, "published", None):
                try:
                    pub = datetime.fromisoformat(entry.published.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pub = None
            if start_date and pub and pub.date() < datetime.strptime(start_date, "%Y-%m-%d").date():
                continue
            if end_date and pub and pub.date() > datetime.strptime(end_date, "%Y-%m-%d").date():
                continue
            articles.append({
                "title": getattr(entry, "title", "") or "",
                "link": getattr(entry, "link", "") or "",
                "published": pub.isoformat() if pub else None,
                "summary": (getattr(entry, "summary", "") or getattr(entry, "description", "") or "")[:500],
                "source": source.get("name", newspaper_id),
            })
        return articles
    except Exception as e:
        logger.exception("scrape_articles failed: %s", e)
        return []
