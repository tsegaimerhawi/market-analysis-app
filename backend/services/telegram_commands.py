"""
Handle Telegram chat commands: buy/sell by symbol or company name.
Supports: buy AAPL 10, sell GME all, buy google stock with all cash balance.
Only processes messages from the chat configured in TELEGRAM_CHAT_ID.
"""

from utils.logger import logger

from services.telegram_notify import get_config, get_updates, send_message

# Last processed update_id so we pass offset to getUpdates and acknowledge updates
_last_update_id = 0

# Common company name -> ticker for "buy google with all cash" style commands
_COMMON_NAMES = {
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "meta": "META",
    "nvidia": "NVDA",
    "netflix": "NFLX",
    "disney": "DIS",
    "walmart": "WMT",
    "jpmorgan": "JPM",
    "jpm": "JPM",
    "visa": "V",
    "mastercard": "MA",
    "berkshire": "BRK.B",
    "coca cola": "KO",
    "pepsi": "PEP",
    "nike": "NKE",
    "adobe": "ADBE",
    "salesforce": "CRM",
    "oracle": "ORCL",
    "intel": "INTC",
    "amd": "AMD",
    "qualcomm": "QCOM",
    "ibm": "IBM",
    "exxon": "XOM",
    "chevron": "CVX",
    "costco": "COST",
    "home depot": "HD",
    "procter": "PG",
    "johnson": "JNJ",
    "pfizer": "PFE",
    "merck": "MRK",
    "abbvie": "ABBV",
    "united health": "UNH",
    "boeing": "BA",
    "lockheed": "LMT",
    "crowdstrike": "CRWD",
    "snowflake": "SNOW",
    "palantir": "PLTR",
    "coinbase": "COIN",
    "robinhood": "HOOD",
    "gamestop": "GME",
    "amc": "AMC",
    "uber": "UBER",
    "lyft": "LYFT",
    "airbnb": "ABNB",
    "spotify": "SPOT",
}


def _resolve_symbol(phrase):
    """Resolve company name or symbol to a valid ticker. Returns symbol or None."""
    if not phrase or not isinstance(phrase, str):
        return None
    phrase = phrase.strip().lower().replace(" stock", "").replace(" stocks", "").strip()
    if not phrase:
        return None
    # Already looks like a ticker (1–5 letters)
    if phrase.isalpha() and 1 <= len(phrase) <= 5:
        from services.company_service import get_quote

        if get_quote(phrase.upper()):
            return phrase.upper()
    if phrase in _COMMON_NAMES:
        return _COMMON_NAMES[phrase]
    # Try as symbol one more time (e.g. BRK.B)
    from services.company_service import get_quote

    cand = phrase.upper().replace(" ", ".")
    if get_quote(cand):
        return cand
    return None


def _parse_buy_all_cash(text):
    """
    Parse "buy X with all cash" / "buy X stock with all cash balance".
    Returns ("buy_all_cash", company_phrase) or None.
    """
    if not text or not isinstance(text, str):
        return None
    t = text.strip().lower()
    if "with all cash" not in t and "all cash balance" not in t:
        return None
    if not t.startswith("buy "):
        return None
    # Drop "buy " and everything from " with all cash..."
    for sep in (" with all cash", " with all cash balance", " all cash balance"):
        if sep in t:
            rest = t[4:].split(sep)[0].strip()  # after "buy "
            if rest:
                return ("buy_all_cash", rest)
            return None
    return None


def _parse_command(text):
    """
    Parse a message into a command or None.
    Returns ("buy"|"sell", symbol, qty_or_all) or None.
    - buy AAPL, buy AAPL 10, /buy AAPL 10 -> ("buy", "AAPL", 10) or ("buy", "AAPL", 1)
    - sell GME, sell GME all, sell GME 5, sell all GME
      -> ("sell", "GME", "all") or ("sell", "GME", 5)
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
    tokens = rest.split()
    # Support "sell all SYMBOL" (e.g. "sell all AAPL")
    if verb == "sell" and len(tokens) >= 2 and (tokens[0] or "").strip().lower() == "all":
        symbol = (tokens[1] or "").strip().upper()
        if symbol and len(symbol) <= 10 and symbol.isalpha():
            return ("sell", symbol, "all")
        return None
    # rest is "SYMBOL" or "SYMBOL 10" or "SYMBOL 0.01" or "SYMBOL[0.01]" or "SYMBOL all"
    first = (tokens[0] or "").strip()
    symbol = first.upper()
    # Support "GOOGL[0.01]" or "GOOGL[10]" format
    if "[" in first and "]" in first:
        try:
            lb = first.index("[")
            rb = first.index("]")
            symbol = first[:lb].strip().upper()
            qty_str = first[lb + 1 : rb].strip()
            if verb == "buy" and symbol and qty_str:
                qty = float(qty_str)
                if qty <= 0:
                    return None
                return ("buy", symbol, qty)
            if verb == "sell" and symbol and qty_str:
                if qty_str.lower() == "all":
                    return ("sell", symbol, "all")
                qty = float(qty_str)
                if qty <= 0:
                    return None
                return ("sell", symbol, qty)
        except (ValueError, TypeError, IndexError):
            pass
        return None
    if not symbol or len(symbol) > 10:
        return None
    if verb == "buy":
        qty = 1
        if len(tokens) >= 2:
            try:
                qty = float(tokens[1])
                if qty <= 0:
                    return None
                # Allow fractional shares (0.01, 0.5, etc.)
            except (ValueError, TypeError):
                return None
        return ("buy", symbol, qty)
    # sell: SYMBOL [qty|all]
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
    from db import execute_buy

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
    from db import execute_sell, get_position

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


def _run_buy_all_cash(symbol):
    """Buy as many shares as possible with full cash balance. Returns (success, message)."""
    from db import execute_buy, get_cash_balance

    from services.company_service import get_quote

    cash = get_cash_balance()
    if cash is None or cash <= 0:
        return False, "No cash balance"
    quote = get_quote(symbol)
    if quote is None:
        return False, f"Could not get price for {symbol}"
    price = quote["price"]
    if price <= 0:
        return False, f"Invalid price for {symbol}"
    qty = int(cash / price)
    if qty < 1:
        return False, f"Insufficient cash (${cash:,.2f}) to buy 1 share of {symbol} (${price:.2f})"
    ok, result, new_cash = execute_buy(symbol, qty, price)
    if not ok:
        return False, str(result)
    return True, (
        f"Bought {qty} {symbol} @ ${price:.2f} (all cash). "
        f"Spent ${cash - new_cash:,.2f}. Remaining cash: ${new_cash:,.2f}"
    )


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
        offset = _last_update_id + 1 if _last_update_id else None
        data = get_updates(token, offset=offset, timeout=8)
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
                "• buy SYMBOL [qty] — e.g. buy AAPL 10, buy GOOGL 0.01 or buy GOOGL[0.01]\n"
                "• sell SYMBOL [qty|all] — e.g. sell GME all or sell all GME\n"
                "• buy X with all cash — e.g. buy google stock with all cash balance\n"
                "• Use symbol or company name (e.g. buy google 10)\n"
                "• /help — this message",
                chat_id=chat_id,
            )
            continue
        # "buy X with all cash" / "buy google stock with all cash balance"
        buy_all_cash = _parse_buy_all_cash(text)
        if buy_all_cash:
            _, company_phrase = buy_all_cash
            symbol = _resolve_symbol(company_phrase)
            if not symbol:
                msg = (
                    f'❌ Unknown company: "{company_phrase}". '
                    "Use a symbol (e.g. GOOGL) or a known company name."
                )
                send_message(msg, chat_id=chat_id)
            else:
                try:
                    success, reply = _run_buy_all_cash(symbol)
                    reply = ("✅ " if success else "❌ ") + reply
                    send_message(reply, chat_id=chat_id)
                except Exception as e:
                    logger.exception("Telegram buy-all-cash failed: %s", e)
                    send_message("❌ Error: " + str(e), chat_id=chat_id)
            continue
        cmd = _parse_command(text)
        if not cmd:
            # Reply so user knows we saw the message and show correct format
            msg = (
                "❓ Use: buy SYMBOL [qty] or sell SYMBOL [qty|all] "
                "(qty can be fractional, e.g. 0.01)\n"
                "Or: buy GOOGL[0.01] or buy X with all cash. Type /help for full list.\n"
                "Type /help for full list."
            )
            send_message(msg, chat_id=chat_id)
            continue
        action, symbol, qty_or_all = cmd
        # Resolve company name to symbol (e.g. "google" -> GOOGL) for normal buy/sell too
        resolved = _resolve_symbol(symbol) or symbol
        reply = None
        try:
            if action == "buy":
                success, reply = _run_buy(resolved, qty_or_all)
            else:
                success, reply = _run_sell(resolved, qty_or_all)
            if not success:
                reply = "❌ " + reply
            else:
                reply = "✅ " + reply
        except Exception as e:
            logger.exception("Telegram command failed: %s", e)
            reply = "❌ Error: " + str(e)
        if reply:
            send_message(reply, chat_id=chat_id)
