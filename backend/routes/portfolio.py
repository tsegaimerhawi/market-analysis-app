from db import (
    add_limit_order,
    adjust_cash,
    cancel_limit_order,
    execute_buy,
    execute_sell,
    get_cash_balance,
    get_initial_balance,
    get_limit_orders,
    get_orders,
    get_pending_limit_orders,
    get_position,
    get_positions,
    mark_limit_order_filled,
    reset_paper_account,
)
from flask import Blueprint, jsonify, request
from services.company_service import get_quote

portfolio_bp = Blueprint("portfolio", __name__)


def _check_pending_limit_orders():
    """Execute any pending limit orders whose price condition is met."""
    for order in get_pending_limit_orders():
        quote = get_quote(order["symbol"])
        if not quote:
            continue
        price = quote["price"]
        sym, side, qty, limit = (
            order["symbol"],
            order["side"],
            order["quantity"],
            float(order["limit_price"]),
        )
        if side == "buy" and price <= limit:
            ok, _, _ = execute_buy(sym, qty, price)
            if ok:
                mark_limit_order_filled(order["id"])
        elif side == "sell" and price >= limit:
            pos = get_position(sym)
            if pos and float(pos["quantity"]) >= qty:
                ok, _, _ = execute_sell(sym, qty, price)
                if ok:
                    mark_limit_order_filled(order["id"])


@portfolio_bp.route("/", methods=["GET"])
def api_portfolio():
    """Return cash balance, initial balance, positions, and recent orders."""
    _check_pending_limit_orders()
    cash = get_cash_balance()
    initial_balance = get_initial_balance()
    positions = get_positions()
    orders = get_orders(limit=30)
    return jsonify(
        {
            "cash_balance": cash,
            "initial_balance": initial_balance,
            "positions": positions,
            "orders": orders,
        }
    )


@portfolio_bp.route("/reset", methods=["POST"])
def api_portfolio_reset():
    """Reset paper account."""
    data = request.get_json(silent=True) or {}
    initial_cash = data.get("initial_cash")
    cash = reset_paper_account(initial_cash=initial_cash)
    return jsonify(
        {
            "message": "Paper account reset.",
            "cash_balance": cash,
            "positions": [],
            "orders": [],
        }
    )


@portfolio_bp.route("/cash", methods=["POST"])
def api_portfolio_cash():
    """Deposit or withdraw paper cash."""
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400
    action = (data.get("action") or "").strip().lower()
    if action not in ("deposit", "withdraw"):
        return jsonify({"error": "Action must be deposit or withdraw"}), 400
    ok, result = adjust_cash(amount, action)
    if not ok:
        return jsonify({"error": result}), 400
    return jsonify({"message": f"{action.capitalize()} ${amount:,.2f}", "cash_balance": result})


# Also including some order-related routes that were in main.py but fit here
@portfolio_bp.route("/order", methods=["POST"])
def api_order():
    """Place a paper trade."""
    data = request.get_json(silent=True) or {}
    symbol = (data.get("symbol") or "").strip().upper()
    side = (data.get("side") or "").strip().lower()
    order_type = (data.get("order_type") or "market").strip().lower()
    try:
        quantity = float(data.get("quantity", 0))
    except (TypeError, ValueError):
        quantity = 0
    try:
        limit_price = float(data.get("limit_price", 0))
    except (TypeError, ValueError):
        limit_price = 0
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    if side not in ("buy", "sell"):
        return jsonify({"error": "Side must be buy or sell"}), 400
    if quantity <= 0:
        return jsonify({"error": "Quantity must be positive"}), 400
    if order_type == "limit":
        if limit_price <= 0:
            return jsonify({"error": "Limit price is required and must be positive"}), 400
        order, err = add_limit_order(symbol, side, quantity, limit_price)
        if err:
            return jsonify({"error": err}), 400
        return jsonify(
            {
                "message": f"Limit {side} {quantity} {symbol} @ {limit_price} (pending)",
                "limit_order": order,
            }
        )
    quote = get_quote(symbol)
    if quote is None:
        return jsonify({"error": "Could not get price for symbol"}), 400
    price = quote["price"]
    if side == "buy":
        ok, result, cash = execute_buy(symbol, quantity, price)
    else:
        ok, result, cash = execute_sell(symbol, quantity, price)
    if not ok:
        return jsonify({"error": result}), 400
    return jsonify(
        {
            "message": f"{side.capitalize()} {quantity} {symbol} @ {price}",
            "positions": result,
            "cash_balance": cash,
        }
    )


@portfolio_bp.route("/limit-orders", methods=["GET"])
def api_limit_orders():
    """Return limit orders."""
    orders = get_limit_orders(limit=50)
    return jsonify({"limit_orders": orders})


@portfolio_bp.route("/limit-orders/<int:order_id>", methods=["DELETE"])
def api_limit_order_cancel(order_id):
    """Cancel a pending limit order."""
    if cancel_limit_order(order_id):
        return jsonify({"message": "Limit order cancelled"})
    return jsonify({"error": "Order not found or already filled/cancelled"}), 404
