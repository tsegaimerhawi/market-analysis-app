"""K-Nearest Neighbors for stock price prediction."""
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from algorithms.base import get_data, compute_metrics, result_dict
from algorithms.features import build_lag_features, train_test_split


def run_algorithm(data_config, source):
    df = get_data(data_config, source)
    if df is None:
        return result_dict("K-Nearest Neighbors", {}, None, None, None, error="Failed to load or filter data")
    X, y, idx = build_lag_features(df["Close"], n_lags=5)
    if X is None:
        return result_dict("K-Nearest Neighbors", {}, None, None, None, error="Insufficient data for features")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_ratio=0.2)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    model = KNeighborsRegressor(n_neighbors=5, weights="distance")
    model.fit(X_train_s, y_train)
    preds = model.predict(X_test_s)
    metrics = compute_metrics(y_test.values, preds)
    return result_dict("K-Nearest Neighbors", metrics, y_test.index, y_test.values, preds)
