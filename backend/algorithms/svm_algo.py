"""Support Vector Machine for stock price prediction."""
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from algorithms.base import compute_metrics, get_data, result_dict
from algorithms.features import build_lag_features, train_test_split


def run_algorithm(data_config, source):
    df = get_data(data_config, source)
    if df is None:
        return result_dict("Support Vector Machine", {}, None, None, None, error="Failed to load or filter data")
    X, y, idx = build_lag_features(df["Close"], n_lags=5)
    if X is None:
        return result_dict("Support Vector Machine", {}, None, None, None, error="Insufficient data for features")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_ratio=0.2)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    model = SVR(kernel="rbf", C=100, gamma="scale")
    model.fit(X_train_s, y_train)
    preds = model.predict(X_test_s)
    metrics = compute_metrics(y_test.values, preds)
    return result_dict("Support Vector Machine", metrics, y_test.index, y_test.values, preds)
