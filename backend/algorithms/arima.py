"""ARIMA for stock price prediction."""

import numpy as np

from algorithms.base import compute_metrics, get_data, result_dict


def run_algorithm(data_config, source):
    df = get_data(data_config, source)
    if df is None or len(df) < 30:
        return result_dict("ARIMA", {}, None, None, None, error="Need at least 30 observations")
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        return result_dict("ARIMA", {}, None, None, None, error="statsmodels not installed")
    series = df["Close"].astype(float)
    n = len(series)
    test_size = max(5, int(n * 0.2))
    train = series.iloc[:-test_size]
    test = series.iloc[-test_size:]
    try:
        model = ARIMA(train, order=(2, 1, 2))
        fit = model.fit()
        preds = fit.forecast(steps=len(test))
        if hasattr(preds, "values"):
            preds = preds.values
        preds = np.asarray(preds)
        if len(preds) > len(test):
            preds = preds[: len(test)]
        elif len(preds) < len(test):
            preds = np.resize(preds, len(test))
        metrics = compute_metrics(test.values, preds)
        return result_dict("ARIMA", metrics, test.index, test.values, preds)
    except Exception as e:
        return result_dict("ARIMA", {}, None, None, None, error=str(e))
