import os
import threading

from config import config
from db import get_agent_enabled, init_db
from flask import Flask
from flask_cors import CORS
from routes import register_routes
from utils.logger import logger

app = Flask(__name__)
CORS(app)

# Ensure watchlist DB exists on startup
init_db()

# Register blueprints
register_routes(app)

# --- Background Loops ---

def _refresh_volatile_list():
    """Update volatile_symbols.json from universe. Called every 30 min."""
    import json

    from services.volatility_scanner import get_volatile_symbols
    
    universe_path = os.path.join(os.path.dirname(__file__), "data", "volatile_universe.json")
    volatile_path = os.path.join(os.path.dirname(__file__), "data", "volatile_symbols.json")
    
    try:
        if not os.path.isfile(universe_path):
            return
        with open(universe_path, "r", encoding="utf-8") as f:
            universe = json.load(f)
        candidates = [str(s).strip().upper() for s in universe if s]
        if not candidates:
            return
        
        symbols = get_volatile_symbols(candidates, top_n=40)
        os.makedirs(os.path.dirname(volatile_path), exist_ok=True)
        with open(volatile_path, "w", encoding="utf-8") as f:
            json.dump(symbols, f, indent=2)
        
        logger.info("Volatile list updated: %d symbols", len(symbols))
        
        try:
            from services.telegram_notify import send_message as send_telegram_message
            display = ", ".join(symbols[:20])
            if len(symbols) > 20:
                display += f" … +{len(symbols) - 20} more"
            msg = f"📊 Volatile stocks updated (30 min)\n{len(symbols)} symbols: {display}"
            send_telegram_message(msg)
        except Exception as te:
            logger.debug("Telegram volatile update notify skipped: %s", te)
    except Exception as e:
        logger.exception("Volatile list refresh failed: %s", e)

def _volatile_refresh_loop():
    import time
    while True:
        try:
            _refresh_volatile_list()
        except Exception as e:
            logger.exception("Volatile refresh loop error: %s", e)
        time.sleep(30 * 60)

def _agent_loop():
    import time
    time.sleep(60)
    while True:
        try:
            if get_agent_enabled():
                from agent_runner import run_agent_cycle
                run_agent_cycle()
            else:
                logger.debug("Agent loop: agent disabled, skipping cycle")
        except Exception as e:
            logger.exception("Agent loop error: %s", e)
        time.sleep(30 * 60)

def _telegram_poll_loop():
    import time

    from services.telegram_notify import get_config
    token, chat_id = get_config()
    if token and chat_id:
        logger.info("Telegram command polling started")
    while True:
        try:
            from services.telegram_commands import process_updates
            process_updates()
        except Exception as e:
            logger.exception("Telegram poll error: %s", e)
        time.sleep(6)

def _limit_order_loop():
    import time

    from routes.portfolio import _check_pending_limit_orders
    while True:
        try:
            _check_pending_limit_orders()
        except Exception as e:
            logger.exception("Limit order loop error: %s", e)
        time.sleep(5 * 60)

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=_volatile_refresh_loop, daemon=True).start()
        threading.Thread(target=_agent_loop, daemon=True).start()
        threading.Thread(target=_telegram_poll_loop, daemon=True).start()
        threading.Thread(target=_limit_order_loop, daemon=True).start()
        logger.info("Background threads started")
    
    use_reloader = os.environ.get("USE_RELOADER", "true").lower() in ("1", "true", "yes")
    app.run(debug=True, port=config.PORT, use_reloader=use_reloader, reloader_type="stat")
