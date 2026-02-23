from flask import Blueprint, jsonify, request
from utils.logger import logger

backtest_bp = Blueprint("backtest", __name__)


@backtest_bp.route("/", methods=["GET"])
def api_backtest():
    """Backtest the trading ensemble on historical data."""
    symbol = (request.args.get("symbol") or "").strip().upper()
    if not symbol:
        return jsonify({"error": "Query parameter 'symbol' required"}), 400
    try:
        days = min(int(request.args.get("days", 90)), 365)
    except (TypeError, ValueError):
        days = 90
    full_control = request.args.get("full_control", "0") == "1"
    try:
        from backtest_runner import run_backtest

        result = run_backtest(symbol, days=days, full_control=full_control)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.exception("Backtest failed: %s", e)
        return jsonify({"error": str(e)}), 500
