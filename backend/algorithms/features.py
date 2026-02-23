"""Feature construction for price prediction (lags, returns, etc.)."""
import pandas as pd


def build_lag_features(series, n_lags=5):
    """Build lagged features from a price series. Returns X (features), y (target), valid index."""
    df = pd.DataFrame({"y": series})
    for i in range(1, n_lags + 1):
        df[f"lag_{i}"] = df["y"].shift(i)
    df["returns"] = df["y"].pct_change().shift(1)
    df = df.dropna()
    if len(df) < 10:
        return None, None, None
    X = df.drop(columns=["y"])
    y = df["y"]
    return X, y, df.index


def train_test_split(X, y, test_ratio=0.2):
    """Split by time: last test_ratio for test."""
    n = len(X)
    test_size = max(1, int(n * test_ratio))
    train_size = n - test_size
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
    return X_train, X_test, y_train, y_test
