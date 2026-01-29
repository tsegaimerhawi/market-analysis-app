"""Shared helpers for stock prediction algorithms."""
import os
import numpy as np
import pandas as pd
from utils.data_handler import load_data


def prepare_data(csv_path, start_date=None, end_date=None):
    """Load CSV and filter by date. Returns DataFrame or None."""
    df = load_data(csv_path)
    if df is None or df.empty:
        return None
    if start_date:
        df = df[df.index >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df.index <= pd.to_datetime(end_date)]
    if df.empty or len(df) < 10:
        return None
    return df


def get_data(data_config, source):
    """
    Get price DataFrame from either a CSV path or a stock symbol (yfinance).
    source: file path (str) or symbol (e.g. 'AAPL').
    Returns DataFrame with Date index and Close (and Open, High, Low, Volume if available).
    """
    start_date = data_config.get("startDate") or None
    end_date = data_config.get("endDate") or None
    if isinstance(source, pd.DataFrame):
        df = source
    elif isinstance(source, str) and os.path.isfile(source):
        df = prepare_data(source, start_date, end_date)
    else:
        # Treat as symbol: fetch from yfinance
        try:
            from services.company_service import get_history
            df = get_history(source, start_date, end_date)
        except Exception:
            df = None
    if df is None or df.empty or len(df) < 10:
        return None
    if start_date:
        df = df[df.index >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df.index <= pd.to_datetime(end_date)]
    if df.empty or len(df) < 10:
        return None
    return df


def compute_metrics(actual, predicted):
    """Compute MAE, RMSE, MAPE, direction_accuracy. Handles NaN."""
    mask = np.isfinite(actual) & np.isfinite(predicted)
    if mask.sum() < 2:
        return {"mae": None, "rmse": None, "mape": None, "direction_accuracy": None}
    a, p = actual[mask], predicted[mask]
    mae = float(np.mean(np.abs(a - p)))
    rmse = float(np.sqrt(np.mean((a - p) ** 2)))
    # MAPE: avoid division by zero
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.abs((a - p) / a)
    pct = pct[np.isfinite(pct)]
    mape = float(np.mean(pct) * 100) if len(pct) > 0 else None
    # Direction: up/down
    dir_actual = np.diff(a) > 0
    dir_pred = np.diff(p) > 0
    direction_accuracy = float(np.mean(dir_actual == dir_pred) * 100) if len(dir_actual) > 0 else None
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": round(mape, 2) if mape is not None else None, "direction_accuracy": round(direction_accuracy, 2) if direction_accuracy is not None else None}


def result_dict(name, metrics, dates, actuals, predictions, error=None):
    """Standard result for API."""
    out = {
        "name": name,
        "metrics": metrics,
        "dates": [str(d) for d in dates] if dates is not None else [],
        "actual": (actuals.tolist() if hasattr(actuals, "tolist") else list(actuals)) if actuals is not None else [],
        "predictions": (predictions.tolist() if hasattr(predictions, "tolist") else list(predictions)) if predictions is not None else [],
    }
    if error:
        out["error"] = error
    return out
