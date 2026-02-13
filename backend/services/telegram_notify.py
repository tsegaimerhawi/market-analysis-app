"""
Send notifications to Telegram when the trading agent has updates (buy/sell, stop-loss, take-profit).
Uses env: TELEGRAM_HTTP_API_KEY (bot token), TELEGRAM_CHAT_ID (destination chat).
Only sends when both are set; no-op otherwise.
"""
import os
from utils.logger import logger

TELEGRAM_API_BASE = "https://api.telegram.org"


def _get_config():
    token = (os.environ.get("TELEGRAM_HTTP_API_KEY") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    return token, chat_id


def send_message(text: str) -> bool:
    """
    Send a text message to the configured Telegram chat.
    Returns True if sent successfully, False otherwise (missing config or API error).
    """
    token, chat_id = _get_config()
    if not token or not chat_id:
        logger.debug("Telegram notify skipped: TELEGRAM_HTTP_API_KEY or TELEGRAM_CHAT_ID not set")
        return False
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload)
            if r.is_success:
                logger.debug("Telegram notify sent to chat_id=%s", chat_id[:8] + "..." if len(chat_id) > 8 else chat_id)
                return True
            logger.warning("Telegram sendMessage failed: %s %s", r.status_code, r.text)
            return False
    except Exception as e:
        logger.warning("Telegram notify error: %s", e)
        return False
