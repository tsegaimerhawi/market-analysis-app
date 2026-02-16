"""
Handle Telegram chat commands: buy SYMBOL [qty], sell SYMBOL [qty|all].
Only processes messages from the chat configured in TELEGRAM_CHAT_ID.
"""
from utils.logger import logger
from services.telegram_notify import get_config, get_updates, send_message


# Last processed update_id so we pass offset to getUpdates and acknowledge updates
_last_update_id = 0


def _parse_command(text):
    """
    Parse a message into a command or None.
    Returns ("buy"|"sell", symbol, qty_or_all) or None.
    - buy AAPL, buy AAPL 10, /buy AAPL 10 -> ("buy", "AAPL", 10) or ("buy", "AAPL", 1)
    - sell GME, sell GME all, sell GME 5, /sell GME -> ("sell", "GME", "all") or ("sell", "GME", 5)
    """
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    # Remove bot command prefix if present
    if text.startswith("/"):
        parts = text[1:].split(maxsplit=2)
    else:
        parts = text.split(maxsplit=2)
    if len(parts) < 2:
        return None
    verb = parts[0].strip().lower()
    rest = (parts[1] + " " + parts[2]).strip() if len(parts) > 2 else parts[1].strip()
    if verb not in ("buy", "sell"):
        return None
    # rest is "SYMBOL" or "SYMBOL 10" or "SYMBOL all"
    tokens = rest.split()
    symbol = (tokens[0] or "").strip().upper()
    if not symbol or len(symbol) > 10:
        return None
    if verb == "buy":
        qty = 1
        if len(tokens) >= 2:
            try:
                qty = float(tokens[1])
                if qty <= 0 or qty != int(qty):
                    return None
                qty = int(qty)
            except (ValueError, TypeError):
                return None
        return ("buy", symbol, qty)
    # sell
    qty_or_all = "all"
    if len(tokens) >= 2:
        if tokens[1].strip().lower() == "all":
            qty_or_all = "all"
        else:
            try:
                q = float(tokens[1])
                if q <= 0:
                    return None
                qty_or_all = int(q) if q == int(q) else q
            except (ValueError, TypeError):
                return None
    return ("sell", symbol, qty_or_all)


def _run_buy(symbol, quantity):
    from db import execute_buy, get_cash_balance
    from services.company_service import get_quote
    quote = get_quote(symbol)
    if quote is None:
        return False, f"Could not get price for {symbol}"
    price = quote["price"]
    ok, result, cash = execute_buy(symbol, quantity, price)
    if not ok:
        return False, str(result)
    return True, f"Bought {quantity} {symbol} @ ${price:.2f}. Cash: ${cash:,.2f}"


def _run_sell(symbol, qty_or_all):
    from db import execute_sell, get_position, get_cash_balance
    from services.company_service import get_quote
    pos = get_position(symbol)
    if not pos:
        return False, f"No position in {symbol}"
    quantity = float(pos.get("quantity") or 0)
    if quantity <= 0:
        return False, f"No position in {symbol}"
    if qty_or_all == "all":
        sell_qty = quantity
    else:
        sell_qty = min(float(qty_or_all), quantity)
    if sell_qty <= 0:
        return False, "Invalid quantity"
    quote = get_quote(symbol)
    if quote is None:
        return False, f"Could not get price for {symbol}"
    price = quote["price"]
    ok, result, cash = execute_sell(symbol, sell_qty, price)
    if not ok:
        return False, str(result)
    return True, f"Sold {sell_qty} {symbol} @ ${price:.2f}. Cash: ${cash:,.2f}"


def process_updates():
    """
    Fetch Telegram updates, process only messages from allowed chat_id.
    Parse buy/sell commands, execute trades, send reply back to the chat.
    """
    global _last_update_id
    token, allowed_chat_id = get_config()
    if not token or not allowed_chat_id:
        return
    try:
        data = get_updates(token, offset=_last_update_id + 1 if _last_update_id else None, timeout=8)
    except Exception as e:
        logger.debug("Telegram getUpdates: %s", e)
        return
    results = data.get("result") or []
    for update in results:
        _last_update_id = max(_last_update_id, update.get("update_id", 0))
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue
        chat_id = msg.get("chat", {}).get("id")
        if chat_id != allowed_chat_id:
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        # Help
        if text.lower() in ("/help", "help", "/start"):
            send_message(
                "📋 Trading commands (paper trading):\n"
                "• buy SYMBOL [qty] — e.g. buy AAPL 10 (default 1)\n"
                "• sell SYMBOL [qty|all] — e.g. sell GME all\n"
                "• /help — this message",
                chat_id=chat_id,
            )
            continue
        cmd = _parse_command(text)
        if not cmd:
            continue
        action, symbol, qty_or_all = cmd
        reply = None
        try:
            if action == "buy":
                success, reply = _run_buy(symbol, qty_or_all)
            else:
                success, reply = _run_sell(symbol, qty_or_all)
            if not success:
                reply = "❌ " + reply
            else:
                reply = "✅ " + reply
        except Exception as e:
            logger.exception("Telegram command failed: %s", e)
            reply = "❌ Error: " + str(e)
        if reply:
            send_message(reply, chat_id=chat_id)
