import os
import json
from flask import Blueprint, request, jsonify
from algorithms import ALGORITHMS
from algorithms.ensemble import run_future_prediction
from utils.imports import UPLOAD_FOLDER
from utils.logger import logger

algorithms_bp = Blueprint('algorithms', __name__)

@algorithms_bp.route("/algorithms", methods=["GET"])
def list_algorithms():
    """Return available algorithm ids and display names."""
    return jsonify({
        "algorithms": [
            {"id": k, "name": v[0]} for k, v in ALGORITHMS.items()
        ]
    })

@algorithms_bp.route("/compare", methods=["POST"])
def compare_algorithms():
    """Run selected algorithms."""
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
            return jsonify({"error": "Provide either symbol or upload a CSV file"}), 400

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

@algorithms_bp.route("/predict-future", methods=["POST"])
def predict_future():
    """Predict future prices and majority trend."""
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
        result = run_future_prediction(data_config, symbol, steps=prediction_length, algorithms=algorithm_ids, registry=ALGORITHMS)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.exception("Future prediction failed")
        return jsonify({"error": str(e)}), 500
