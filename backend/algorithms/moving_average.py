"""Moving Average (double SMA) for stock price prediction."""
import numpy as np
import pandas as pd

from algorithms.base import compute_metrics, get_data, result_dict


def run_algorithm(data_config, source):
    df = get_data(data_config, source)
    if df is None or len(df) < 20:
        return result_dict("Moving Average", {}, None, None, None, error="Need at least 20 observations")
    series = df["Close"].astype(float)
    n = len(series)
    test_size = max(5, int(n * 0.2))
    train = series.iloc[:-test_size]
    test = series.iloc[-test_size:]
    short, long_ = 5, 15
    sma_short = train.rolling(short).mean()
    sma_long = train.rolling(long_).mean()
    # Predict: next price = current price * (SMA_short / SMA_long) momentum
    preds = []
    for i in range(len(test)):
        if i == 0:
            window = pd.concat([train.iloc[-long_:], test.iloc[:1]])
        else:
            window = pd.concat([train, test.iloc[:i]]).iloc[-long_:]
        if len(window) < long_:
            preds.append(float(window.iloc[-1]))
            continue
        sma_s = window.rolling(short).mean().iloc[-1]
        sma_l = window.rolling(long_).mean().iloc[-1]
        last_price = window.iloc[-1]
        if np.isfinite(sma_l) and sma_l != 0:
            preds.append(float(last_price * (sma_s / sma_l)))
        else:
            preds.append(float(last_price))
    preds = np.array(preds)
    if len(preds) != len(test):
        preds = np.resize(preds, len(test))
    metrics = compute_metrics(test.values, preds)
    return result_dict("Moving Average", metrics, test.index, test.values, preds)
