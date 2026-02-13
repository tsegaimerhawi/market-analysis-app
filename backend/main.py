from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from utils.imports import UPLOAD_FOLDER
from utils.logger import logger
from algorithms import ALGORITHMS
from db import (
    init_db,
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    get_cash_balance,
    get_positions,
    get_orders,
    get_position,
    execute_buy,
    execute_sell,
    reset_paper_account,
    adjust_cash,
    get_initial_balance,
    add_limit_order,
    get_limit_orders,
    get_pending_limit_orders,
    mark_limit_order_filled,
    cancel_limit_order,
    get_agent_enabled,
    set_agent_enabled,
    get_agent_include_volatile,
    set_agent_include_volatile,
    get_agent_stop_loss_pct,
    set_agent_stop_loss_pct,
    get_agent_take_profit_pct,
    set_agent_take_profit_pct,
    get_agent_reasoning,
    get_agent_history,
)
from services.company_service import get_history, get_info, get_quote, search as company_search
from services.article_service import get_newspapers, scrape_articles
from algorithms.ensemble import run_future_prediction

app = Flask(__name__)
CORS(app)

# Ensure watchlist DB exists on startup
init_db()


@app.route("/api/watchlist", methods=["GET"])
def api_watchlist():
    """Return the user's watchlist (all saved companies)."""
    items = get_watchlist()
    return jsonify({"watchlist": items})


@app.route("/api/watchlist", methods=["POST"])
def api_watchlist_add():
    """Add a company to the watchlist. Body: { "symbol": "AAPL", "company_name": "Apple Inc." } (company_name optional)."""
    data = request.get_json(silent=True) or {}
    symbol = (data.get("symbol") or request.form.get("symbol") or "").strip().upper()
    company_name = data.get("company_name") or request.form.get("company_name")
    if not symbol:
        return jsonify({"error": "symbol is required"}), 400
    item = add_to_watchlist(symbol, company_name)
    if item is None:
        return jsonify({"error": "Symbol already in watchlist or invalid"}), 409
    return jsonify({"watchlist": get_watchlist(), "added": item})


@app.route("/api/watchlist/<symbol_or_id>", methods=["DELETE"])
def api_watchlist_remove(symbol_or_id):
    """Remove a company by symbol (e.g. AAPL) or by id."""
    if remove_from_watchlist(symbol_or_id):
        return jsonify({"watchlist": get_watchlist()})
    return jsonify({"error": "Not found"}), 404


@app.route("/api/company/<symbol>", methods=["GET"])
def api_company_info(symbol):
    """Get full company info from yfinance (everything in the system)."""
    info = get_info(symbol)
    if info is None:
        return jsonify({"error": "Invalid symbol"}), 400
    return jsonify(info)


@app.route("/api/company/search", methods=["GET"])
def api_company_search():
    """Search for a ticker by symbol. Query param: q=AAPL."""
    q = request.args.get("q", "").strip()
    results = company_search(q)
    return jsonify({"results": results})


@app.route("/api/newspapers", methods=["GET"])
def api_newspapers():
    """Return list of newspapers (id, name) for the Scrape Articles dropdown."""
    papers = get_newspapers()
    return jsonify({"newspapers": [{"id": p["id"], "name": p["name"]} for p in papers]})


@app.route("/api/scrape-articles", methods=["POST"])
def api_scrape_articles():
    """Scrape articles. Body or form: newspaper (id), startDate, endDate."""
    data = request.get_json(silent=True) or {}
    newspaper = data.get("newspaper") or request.form.get("newspaper")
    start_date = data.get("startDate") or request.form.get("startDate")
    end_date = data.get("endDate") or request.form.get("endDate")
    if not newspaper:
        return jsonify({"error": "newspaper is required", "articles": []}), 400
    articles = scrape_articles(newspaper, start_date, end_date)
    return jsonify({"articles": articles})


@app.route("/api/companies", methods=["GET"])
def api_companies_list():
    """Return all companies (symbol + name) for the watchlist option field."""
    path = os.path.join(os.path.dirname(__file__), "data", "companies.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            companies = json.load(f)
        return jsonify({"companies": companies})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug("companies list load failed: %s", e)
        return jsonify({"companies": []})


@app.route("/api/compare", methods=["POST"])
def compare_algorithms():
    """
    Run selected algorithms. Either:
    - symbol: company symbol from watchlist (data fetched via yfinance), or
    - dataFile: CSV file upload (legacy).
    Form: startDate, endDate, algorithms (JSON array), and either symbol or dataFile.
    """
    logger.debug("compare_algorithms: request received")
    start_date = request.form.get("startDate") or None
    end_date = request.form.get("endDate") or None
    algorithms_param = request.form.get("algorithms")
    try:
        algorithm_ids = json.loads(algorithms_param) if algorithms_param else list(ALGORITHMS.keys())
    except json.JSONDecodeError:
        algorithm_ids = list(ALGORITHMS.keys())

    source = None
    symbol = request.form.get("symbol", "").strip().upper()
    if symbol:
        source = symbol
    else:
        file = request.files.get("dataFile")
        if file and file.filename:
            if not file.filename.lower().endswith(".csv"):
                return jsonify({"error": "File must be a CSV"}), 400
            csv_path = os.path.join(UPLOAD_FOLDER, file.filename)
            try:
                file.save(csv_path)
                source = csv_path
            except Exception as e:
                return jsonify({"error": f"Failed to save file: {str(e)}"}), 500
        else:
            return jsonify({"error": "Provide either symbol (company from watchlist) or upload a CSV file"}), 400

    data_config = {"startDate": start_date, "endDate": end_date}
    results = []
    for algo_id in algorithm_ids:
        if algo_id not in ALGORITHMS:
            continue
        name, run_fn = ALGORITHMS[algo_id]
        try:
            result = run_fn(data_config, source)
            results.append(result)
        except Exception as e:
            logger.exception("Algorithm %s failed", algo_id)
            results.append({
                "name": name,
                "error": str(e),
                "metrics": {},
                "dates": [],
                "actual": [],
                "predictions": [],
            })

    return jsonify({"results": results})


@app.route("/api/predict-future", methods=["POST"])
def predict_future():
    """
    Predict future prices and majority trend.
    Body: symbol, startDate, endDate, prediction_length, algorithms (optional)
    """
    data = request.get_json(silent=True) or {}
    symbol = (data.get("symbol") or request.form.get("symbol") or "").strip().upper()
    start_date = data.get("startDate") or request.form.get("startDate") or None
    end_date = data.get("endDate") or request.form.get("endDate") or None
    prediction_length = int(data.get("prediction_length") or request.form.get("prediction_length") or 7)
    algorithms_param = data.get("algorithms") or request.form.get("algorithms")
    
    try:
        algorithm_ids = json.loads(algorithms_param) if isinstance(algorithms_param, str) else (algorithms_param or ["linear_regression", "random_forest", "xgboost"])
    except json.JSONDecodeError:
        algorithm_ids = ["linear_regression", "random_forest", "xgboost"]

    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    data_config = {"startDate": start_date, "endDate": end_date}
    try:
        result = run_future_prediction(data_config, symbol, steps=prediction_length, algorithms=algorithm_ids)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.exception("Future prediction failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/algorithms", methods=["GET"])
def list_algorithms():
    """Return available algorithm ids and display names."""
    return jsonify({
        "algorithms": [
            {"id": k, "name": v[0]} for k, v in ALGORITHMS.items()
        ]
    })


# --- Paper trading: portfolio, quote, order ---

def _check_pending_limit_orders():
    """Execute any pending limit orders whose price condition is met."""
    for order in get_pending_limit_orders():
        quote = get_quote(order["symbol"])
        if not quote:
            continue
        price = quote["price"]
        sym, side, qty, limit = order["symbol"], order["side"], order["quantity"], float(order["limit_price"])
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


@app.route("/api/portfolio", methods=["GET"])
def api_portfolio():
    """Return cash balance, initial balance (for return %), positions, and recent orders."""
    _check_pending_limit_orders()
    cash = get_cash_balance()
    initial_balance = get_initial_balance()
    positions = get_positions()
    orders = get_orders(limit=30)
    return jsonify({
        "cash_balance": cash,
        "initial_balance": initial_balance,
        "positions": positions,
        "orders": orders,
    })


@app.route("/api/portfolio/reset", methods=["POST"])
def api_portfolio_reset():
    """Reset paper account: cash to default, clear all positions and orders."""
    cash = reset_paper_account()
    return jsonify({
        "message": "Paper account reset.",
        "cash_balance": cash,
        "positions": [],
        "orders": [],
    })


@app.route("/api/portfolio/cash", methods=["POST"])
def api_portfolio_cash():
    """Deposit or withdraw paper cash. Body: { "amount": 1000, "action": "deposit"|"withdraw" }."""
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


@app.route("/api/quote/<symbol>", methods=["GET"])
def api_quote(symbol):
    """Get current price (quote) for a symbol."""
    quote = get_quote(symbol)
    if quote is None:
        return jsonify({"error": "Invalid symbol or no quote"}), 400
    return jsonify(quote)


@app.route("/api/order", methods=["POST"])
def api_order():
    """
    Place a paper trade. Body: { "symbol", "side": "buy"|"sell", "quantity", "order_type": "market"|"limit", "limit_price" (if limit) }.
    Market: uses live quote. Limit: stored and executed when price is reached (checked on portfolio load).
    """
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
        return jsonify({
            "message": f"Limit {side} {quantity} {symbol} @ {limit_price} (pending)",
            "limit_order": order,
        })
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
    return jsonify({
        "message": f"{side.capitalize()} {quantity} {symbol} @ {price}",
        "positions": result,
        "cash_balance": cash,
    })


@app.route("/api/limit-orders", methods=["GET"])
def api_limit_orders():
    """Return limit orders (pending first)."""
    orders = get_limit_orders(limit=50)
    return jsonify({"limit_orders": orders})


@app.route("/api/limit-orders/<int:order_id>", methods=["DELETE"])
def api_limit_order_cancel(order_id):
    """Cancel a pending limit order."""
    if cancel_limit_order(order_id):
        return jsonify({"message": "Limit order cancelled"})
    return jsonify({"error": "Order not found or already filled/cancelled"}), 404


# --- Trading agent ---

@app.route("/api/agent/status", methods=["GET"])
def api_agent_status():
    """Return agent enabled, include_volatile, stop_loss_pct, take_profit_pct."""
    return jsonify({
        "enabled": get_agent_enabled(),
        "include_volatile": get_agent_include_volatile(),
        "stop_loss_pct": get_agent_stop_loss_pct(),
        "take_profit_pct": get_agent_take_profit_pct(),
    })


@app.route("/api/agent/status", methods=["POST"])
def api_agent_set_status():
    """Turn agent on/off, include_volatile, stop_loss_pct, take_profit_pct. Body: { "enabled", "include_volatile", "stop_loss_pct", "take_profit_pct" }."""
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
    return jsonify({
        "enabled": get_agent_enabled(),
        "include_volatile": get_agent_include_volatile(),
        "stop_loss_pct": get_agent_stop_loss_pct(),
        "take_profit_pct": get_agent_take_profit_pct(),
    })


@app.route("/api/agent/volatile-symbols", methods=["GET"])
def api_agent_volatile_symbols():
    """Return volatile symbols from 8h volatility algorithm (candidates from data/volatile_symbols.json). Query: scores=1 for volatility scores."""
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


@app.route("/api/agent/reasoning", methods=["GET"])
def api_agent_reasoning():
    """Return recent reasoning steps. Query: limit=100, symbol=AAPL (optional)."""
    limit = min(int(request.args.get("limit", 100)), 500)
    symbol = request.args.get("symbol", "").strip().upper() or None
    steps = get_agent_reasoning(limit=limit, symbol=symbol)
    return jsonify({"reasoning": steps})


@app.route("/api/agent/history", methods=["GET"])
def api_agent_history():
    """Return agent decision/trade history."""
    limit = min(int(request.args.get("limit", 50)), 200)
    entries = get_agent_history(limit=limit)
    return jsonify({"history": entries})


@app.route("/api/agent/run", methods=["POST"])
def api_agent_run_once():
    """Trigger one agent cycle manually (runs in request; may be slow)."""
    try:
        from agent_runner import run_agent_cycle
        run_agent_cycle()
        return jsonify({"message": "Cycle completed"})
    except Exception as e:
        logger.exception("Agent run failed")
        return jsonify({"error": str(e)}), 500


def _agent_loop():
    """Background loop: every 5 minutes run agent cycle if enabled."""
    import time
    while True:
        time.sleep(300)  # 5 min
        try:
            if get_agent_enabled():
                from agent_runner import run_agent_cycle
                run_agent_cycle()
        except Exception as e:
            logger.exception("Agent loop error: %s", e)


if __name__ == "__main__":
    import threading
    # Start agent background thread in the reloader child (where Flask runs)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        agent_thread = threading.Thread(target=_agent_loop, daemon=True)
        agent_thread.start()
    port = int(os.environ.get("PORT", 5001))
    try:
        app.run(debug=True, port=port, use_reloader=True, reloader_type="stat")
    except TypeError:
        app.run(debug=True, port=port, use_reloader=False)
