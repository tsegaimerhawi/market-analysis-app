import os
import json
from flask import Blueprint, request, jsonify
from services.article_service import get_newspapers, scrape_articles
from utils.logger import logger

articles_bp = Blueprint('articles', __name__)

@articles_bp.route("/newspapers", methods=["GET"])
def api_newspapers():
    """Return list of newspapers."""
    papers = get_newspapers()
    return jsonify({"newspapers": [{"id": p["id"], "name": p["name"]} for p in papers]})

@articles_bp.route("/scrape-articles", methods=["POST"])
def api_scrape_articles():
    """Scrape articles."""
    data = request.get_json(silent=True) or {}
    newspaper = data.get("newspaper") or request.form.get("newspaper")
    start_date = data.get("startDate") or request.form.get("startDate")
    end_date = data.get("endDate") or request.form.get("endDate")
    if not newspaper:
        return jsonify({"error": "newspaper is required", "articles": []}), 400
    articles = scrape_articles(newspaper, start_date, end_date)
    return jsonify({"articles": articles})

@articles_bp.route("/companies", methods=["GET"])
def api_companies_list():
    """Return all companies (symbol + name) for the watchlist option field."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "companies.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            companies = json.load(f)
        return jsonify({"companies": companies})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug("companies list load failed: %s", e)
        return jsonify({"companies": []})
