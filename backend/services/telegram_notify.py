"""
Send notifications to Telegram when the trading agent has updates (buy/sell, stop-loss, take-profit).
Uses env: TELEGRAM_HTTP_API_KEY (bot token), TELEGRAM_CHAT_ID (destination chat).
Only sends when both are set; no-op otherwise.

Chat ID: use your numeric user id (e.g. 123456789) or a group id (negative number).
Get it by messaging @userinfobot or by calling getUpdates on your bot after you send /start.
"""
import os
from utils.logger import logger

TELEGRAM_API_BASE = "https://api.telegram.org"


def _get_config():
    token = (os.environ.get("TELEGRAM_HTTP_API_KEY") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    raw = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    # Telegram accepts int or string; use int for numeric ids to avoid whitespace/format issues
    if raw and raw.lstrip("-").isdigit():
        chat_id = int(raw)
    else:
        chat_id = raw
    return token, chat_id


def send_message(text: str):
    """
    Send a text message to the configured Telegram chat.
    Returns (True, None) if sent successfully, (False, error_message) otherwise.
    """
    token, chat_id = _get_config()
    if not token or not chat_id:
        logger.debug("Telegram notify skipped: TELEGRAM_HTTP_API_KEY or TELEGRAM_CHAT_ID not set")
        return False, "TELEGRAM_HTTP_API_KEY or TELEGRAM_CHAT_ID not set"
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload)
            if r.is_success:
                logger.debug("Telegram notify sent to chat_id=%s", str(chat_id)[:10] + "..." if len(str(chat_id)) > 10 else chat_id)
                return True, None
            # Surface Telegram's error (e.g. "chat not found", "user hasn't started the bot")
            try:
                data = r.json()
                desc = data.get("description") or data.get("error_description") or r.text
            except Exception:
                desc = r.text
            logger.warning("Telegram sendMessage failed: %s %s", r.status_code, desc)
            return False, desc or f"HTTP {r.status_code}"
    except Exception as e:
        logger.warning("Telegram notify error: %s", e)
        return False, str(e)
