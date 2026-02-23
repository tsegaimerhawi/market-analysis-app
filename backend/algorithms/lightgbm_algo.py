"""LightGBM for stock price prediction."""

from algorithms.base import compute_metrics, get_data, result_dict
from algorithms.features import build_lag_features, train_test_split


def run_algorithm(data_config, source):
    try:
        import lightgbm as lgb
    except ImportError:
        return result_dict("LightGBM", {}, None, None, None, error="lightgbm not installed")

    df = get_data(data_config, source)
    if df is None:
        return result_dict("LightGBM", {}, None, None, None, error="Failed to load or filter data")

    X, y, idx = build_lag_features(df["Close"], n_lags=5)
    if X is None:
        return result_dict("LightGBM", {}, None, None, None, error="Insufficient data for features")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_ratio=0.2)

    model = lgb.LGBMRegressor(
        n_estimators=100, learning_rate=0.05, num_leaves=31, random_state=42, verbose=-1
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    metrics = compute_metrics(y_test.values, preds)
    return result_dict("LightGBM", metrics, y_test.index, y_test.values, preds)
