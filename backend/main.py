from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from utils.imports import UPLOAD_FOLDER
from utils.logger import logger
from algorithms import ALGORITHMS
from db import init_db, get_watchlist, add_to_watchlist, remove_from_watchlist
from services.company_service import get_history, get_info, search as company_search
from services.article_service import get_newspapers, scrape_articles

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


@app.route("/api/algorithms", methods=["GET"])
def list_algorithms():
    """Return available algorithm ids and display names."""
    return jsonify({
        "algorithms": [
            {"id": k, "name": v[0]} for k, v in ALGORITHMS.items()
        ]
    })


if __name__ == "__main__":
    try:
        app.run(debug=True, port=5000, use_reloader=True, reloader_type="stat")
    except TypeError:
        app.run(debug=True, port=5000, use_reloader=False)
