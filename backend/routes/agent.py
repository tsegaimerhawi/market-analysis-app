import os
import json
from flask import Blueprint, request, jsonify
from db import (
    get_agent_enabled, set_agent_enabled, get_agent_include_volatile,
    set_agent_include_volatile, get_agent_stop_loss_pct, set_agent_stop_loss_pct,
    get_agent_take_profit_pct, set_agent_take_profit_pct, get_agent_full_control,
    set_agent_full_control, get_agent_reasoning, get_agent_history
)
from utils.logger import logger

agent_bp = Blueprint('agent', __name__)

def _volatile_candidates_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "volatile_symbols.json")

def _volatile_universe_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "volatile_universe.json")

def _normal_candidates_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "normal_symbols.json")

@agent_bp.route("/status", methods=["GET"])
def api_agent_status():
    return jsonify({
        "enabled": get_agent_enabled(),
        "include_volatile": get_agent_include_volatile(),
        "stop_loss_pct": get_agent_stop_loss_pct(),
        "take_profit_pct": get_agent_take_profit_pct(),
        "full_control": get_agent_full_control(),
    })

@agent_bp.route("/status", methods=["POST"])
def api_agent_set_status():
    data = request.get_json(silent=True) or {}
    if "enabled" in data:
        set_agent_enabled(bool(data["enabled"]))
    if "include_volatile" in data:
        set_agent_include_volatile(bool(data["include_volatile"]))
    if "stop_loss_pct" in data:
        v = data["stop_loss_pct"]
        set_agent_stop_loss_pct(float(v) if v is not None and str(v).strip() else None)
    if "take_profit_pct" in data:
        v = data["take_profit_pct"]
        set_agent_take_profit_pct(float(v) if v is not None and str(v).strip() else None)
    if "full_control" in data:
        set_agent_full_control(bool(data["full_control"]))
    return api_agent_status()

@agent_bp.route("/normal-candidates", methods=["GET"])
def api_normal_candidates_get():
    try:
        path = _normal_candidates_path()
        if not os.path.isfile(path):
            return jsonify({"symbols": []})
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        symbols = [str(s).strip().upper() for s in data if s]
        return jsonify({"symbols": symbols})
    except Exception as e:
        logger.exception("normal-candidates get failed: %s", e)
        return jsonify({"symbols": [], "error": str(e)})

@agent_bp.route("/normal-candidates", methods=["PUT"])
def api_normal_candidates_put():
    try:
        data = request.get_json(silent=True) or {}
        symbols = data.get("symbols")
        if not isinstance(symbols, list):
            return jsonify({"error": "Body must include 'symbols' array"}), 400
        normalized = list(dict.fromkeys([str(s).strip().upper() for s in symbols if str(s).strip()]))
        path = _normal_candidates_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2)
        return jsonify({"symbols": normalized, "message": "Saved"})
    except Exception as e:
        logger.exception("normal-candidates put failed: %s", e)
        return jsonify({"error": str(e)}), 500

@agent_bp.route("/volatile-candidates", methods=["GET"])
def api_volatile_candidates_get():
    try:
        path = _volatile_candidates_path()
        if not os.path.isfile(path):
            return jsonify({"symbols": []})
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        symbols = [str(s).strip().upper() for s in data if s]
        return jsonify({"symbols": symbols})
    except Exception as e:
        logger.exception("volatile-candidates get failed: %s", e)
        return jsonify({"symbols": [], "error": str(e)})

@agent_bp.route("/volatile-candidates", methods=["PUT"])
def api_volatile_candidates_put():
    try:
        data = request.get_json(silent=True) or {}
        symbols = data.get("symbols")
        if not isinstance(symbols, list):
            return jsonify({"error": "Body must include 'symbols' array"}), 400
        normalized = list(dict.fromkeys([str(s).strip().upper() for s in symbols if str(s).strip()]))
        path = _volatile_candidates_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2)
        return jsonify({"symbols": normalized, "message": "Saved"})
    except Exception as e:
        logger.exception("volatile-candidates put failed: %s", e)
        return jsonify({"error": str(e)}), 500

@agent_bp.route("/volatile-candidates/refresh-from-universe", methods=["POST"])
def api_volatile_candidates_refresh():
    try:
        universe_path = _volatile_universe_path()
        if not os.path.isfile(universe_path):
            return jsonify({"error": "data/volatile_universe.json not found"}), 404
        with open(universe_path, "r", encoding="utf-8") as f:
            universe = json.load(f)
        candidates = [str(s).strip().upper() for s in universe if s]
        if not candidates:
            return jsonify({"error": "volatile_universe.json is empty"}), 400
        from services.volatility_scanner import get_volatile_symbols
        top_n = min(int(request.args.get("top_n", 40)), 100)
        symbols = get_volatile_symbols(candidates, top_n=top_n)
        path = _volatile_candidates_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(symbols, f, indent=2)
        return jsonify({"symbols": symbols, "message": f"Updated from universe (top {len(symbols)} by volatility)"})
    except Exception as e:
        logger.exception("volatile-candidates refresh failed: %s", e)
        return jsonify({"error": str(e)}), 500

@agent_bp.route("/volatile-symbols", methods=["GET"])
def api_agent_volatile_symbols():
    try:
        from services.volatility_scanner import get_candidate_symbols_from_file, get_volatile_symbols_with_scores, get_volatile_symbols
        candidates = get_candidate_symbols_from_file()
        if not candidates:
            return jsonify({"symbols": [], "source": "algorithm"})
        if request.args.get("scores") == "1":
            ranked = get_volatile_symbols_with_scores(candidates, top_n=25)
            return jsonify({"symbols": [r["symbol"] for r in ranked], "with_scores": ranked, "source": "algorithm"})
        symbols = get_volatile_symbols(candidates, top_n=25)
        return jsonify({"symbols": symbols, "source": "algorithm"})
    except Exception as e:
        logger.exception("volatile-symbols failed: %s", e)
        return jsonify({"symbols": [], "error": str(e)})

@agent_bp.route("/reasoning", methods=["GET"])
def api_agent_reasoning():
    limit = min(int(request.args.get("limit", 100)), 500)
    symbol = request.args.get("symbol", "").strip().upper() or None
    steps = get_agent_reasoning(limit=limit, symbol=symbol)
    return jsonify({"reasoning": steps})

@agent_bp.route("/history", methods=["GET"])
def api_agent_history():
    limit = min(int(request.args.get("limit", 50)), 200)
    entries = get_agent_history(limit=limit)
    return jsonify({"history": entries})

@agent_bp.route("/run", methods=["POST"])
def api_agent_run_once():
    try:
        from agent_runner import run_agent_cycle
        run_agent_cycle()
        return jsonify({"message": "Cycle completed"})
    except Exception as e:
        logger.exception("Agent run failed")
        return jsonify({"error": str(e)}), 500

@agent_bp.route("/telegram-test", methods=["GET", "POST"])
def api_agent_telegram_test():
    try:
        from services.telegram_notify import send_message as send_telegram_message
        msg = "🤖 Trading Agent test — if you see this, Telegram is working."
        ok, err = send_telegram_message(msg)
        if ok:
            return jsonify({"ok": True, "message": "Test message sent to Telegram"})
        return jsonify({"ok": False, "error": err or "Set TELEGRAM_HTTP_API_KEY and TELEGRAM_CHAT_ID."})
    except Exception as e:
        logger.exception("Telegram test failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
