from flask import Blueprint, request, jsonify
from db import get_watchlist, add_to_watchlist, remove_from_watchlist

watchlist_bp = Blueprint('watchlist', __name__)

@watchlist_bp.route("/", methods=["GET"])
def api_watchlist():
    """Return the user's watchlist (all saved companies)."""
    items = get_watchlist()
    return jsonify({"watchlist": items})

@watchlist_bp.route("/", methods=["POST"])
def api_watchlist_add():
    """Add a company to the watchlist."""
    data = request.get_json(silent=True) or {}
    symbol = (data.get("symbol") or request.form.get("symbol") or "").strip().upper()
    company_name = data.get("company_name") or request.form.get("company_name")
    if not symbol:
        return jsonify({"error": "symbol is required"}), 400
    item = add_to_watchlist(symbol, company_name)
    if item is None:
        return jsonify({"error": "Symbol already in watchlist or invalid"}), 409
    return jsonify({"watchlist": get_watchlist(), "added": item})

@watchlist_bp.route("/<symbol_or_id>", methods=["DELETE"])
def api_watchlist_remove(symbol_or_id):
    """Remove a company by symbol or by id."""
    if remove_from_watchlist(symbol_or_id):
        return jsonify({"watchlist": get_watchlist()})
    return jsonify({"error": "Not found"}), 404
