"""Simple LSTM for stock price prediction."""
import numpy as np
from algorithms.base import get_data, compute_metrics, result_dict

# Default sequence length and model size for a "simple" LSTM
SEQ_LEN = 20
UNITS = 32
EPOCHS = 30
BATCH_SIZE = 32
TEST_RATIO = 0.2


def build_sequences(series, seq_len):
    """Build (X, y) for LSTM: X has shape (n_samples, seq_len, 1), y is next value."""
    vals = series.values.astype(np.float32)
    if len(vals) < seq_len + 10:
        return None, None, None
    X, y = [], []
    for i in range(seq_len, len(vals)):
        X.append(vals[i - seq_len : i])
        y.append(vals[i])
    X = np.array(X).reshape(-1, seq_len, 1)
    y = np.array(y)
    idx = series.index[seq_len:]
    return X, y, idx


def train_test_split_seq(X, y, idx, test_ratio=TEST_RATIO):
    """Time-based split: last test_ratio for test."""
    n = len(X)
    test_size = max(1, int(n * test_ratio))
    train_size = n - test_size
    return (
        X[:train_size], X[train_size:],
        y[:train_size], y[train_size:],
        idx[:train_size], idx[train_size:],
    )


def _get_keras_model(seq_len, units=UNITS):
    """Build and return compiled Keras LSTM model."""
    from tensorflow import keras
    from tensorflow.keras import layers
    model = keras.Sequential([
        layers.Input(shape=(seq_len, 1)),
        layers.LSTM(units, activation="tanh"),
        layers.Dense(1),
    ])
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3), loss="mse", metrics=["mae"])
    return model


def predict_future_steps(model, last_prices, steps, seq_len, min_val=0, range_val=1):
    """Predict next `steps` values recursively. last_prices: array of length seq_len."""
    preds = []
    # Scale the input window
    window = [(p - min_val) / range_val for p in last_prices]
    for _ in range(steps):
        X = np.array(window[-seq_len:], dtype=np.float32).reshape(1, seq_len, 1)
        next_val_scaled = float(model.predict(X, verbose=0)[0, 0])
        preds.append(next_val_scaled * range_val + min_val)
        window.append(next_val_scaled)
    return preds


def run_algorithm(data_config, source):
    df = get_data(data_config, source)
    if df is None:
        return result_dict("LSTM", {}, None, None, None, error="Failed to load or filter data")

    try:
        from tensorflow import keras
    except ImportError:
        return result_dict(
            "LSTM", {}, None, None, None,
            error="LSTM requires TensorFlow. Install with: pip install tensorflow"
        )

    series = df["Close"]
    min_val = float(series.min())
    max_val = float(series.max())
    range_val = max_val - min_val if max_val > min_val else 1.0
    
    scaled_series = (series - min_val) / range_val
    
    X, y, idx = build_sequences(scaled_series, SEQ_LEN)
    if X is None:
        return result_dict("LSTM", {}, None, None, None, error="Insufficient data for sequences (need at least {} points)".format(SEQ_LEN + 10))

    X_train, X_test, y_train, y_test, _, idx_test = train_test_split_seq(X, y, idx)

    model = _get_keras_model(SEQ_LEN)
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=min(BATCH_SIZE, len(X_train)), verbose=0)

    preds_scaled = model.predict(X_test, verbose=0).flatten()
    preds = preds_scaled * range_val + min_val
    y_test_unscaled = y_test * range_val + min_val
    
    metrics = compute_metrics(y_test_unscaled, preds)
    return result_dict("LSTM", metrics, idx_test, y_test_unscaled, preds)
