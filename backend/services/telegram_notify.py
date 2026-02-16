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


def get_config():
    """Return (token, chat_id) for use by command handler. Both may be empty."""
    return _get_config()


def get_updates(token, offset=None, timeout=10):
    """
    Fetch updates from Telegram (for polling). Returns JSON response with result list of updates.
    """
    if not token:
        return {}
    url = f"{TELEGRAM_API_BASE}/bot{token}/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        import httpx
        with httpx.Client(timeout=float(timeout) + 5) as client:
            r = client.get(url, params=params)
            if r.is_success:
                return r.json() or {}
    except Exception as e:
        logger.debug("Telegram getUpdates error: %s", e)
    return {}


def send_message(text: str, chat_id=None, parse_mode=None):
    """
    Send a text message to Telegram.
    If chat_id is provided, send to that chat; otherwise use TELEGRAM_CHAT_ID from config.
    parse_mode: optional "Markdown" or "HTML" for formatting.
    Returns (True, None) if sent successfully, (False, error_message) otherwise.
    """
    token, config_chat_id = _get_config()
    if not token:
        logger.debug("Telegram notify skipped: TELEGRAM_HTTP_API_KEY or TELEGRAM_BOT_TOKEN not set")
        return False, "TELEGRAM_HTTP_API_KEY or TELEGRAM_BOT_TOKEN not set"
    dest = chat_id if chat_id is not None else config_chat_id
    if not dest:
        logger.debug("Telegram notify skipped: no chat_id (set TELEGRAM_CHAT_ID or pass chat_id)")
        return False, "TELEGRAM_CHAT_ID not set"
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {"chat_id": dest, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload)
            if r.is_success:
                logger.debug("Telegram notify sent to chat_id=%s", str(dest)[:10] + "..." if len(str(dest)) > 10 else dest)
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
