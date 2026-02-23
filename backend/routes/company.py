from flask import Blueprint, jsonify, request
from services.company_service import get_info
from services.company_service import search as company_search

company_bp = Blueprint('company', __name__)

@company_bp.route("/<symbol>", methods=["GET"])
def api_company_info(symbol):
    """Get full company info."""
    info = get_info(symbol)
    if info is None:
        return jsonify({"error": "Invalid symbol"}), 400
    return jsonify(info)

@company_bp.route("/search", methods=["GET"])
def api_company_search():
    """Search for a ticker by symbol."""
    q = request.args.get("q", "").strip()
    results = company_search(q)
    return jsonify({"results": results})
