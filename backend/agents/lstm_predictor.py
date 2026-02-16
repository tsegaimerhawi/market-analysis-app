"""
LSTM predictor: uses a small Keras LSTM on recent price history when available.
Trains on last N days of returns, predicts next-step return -> confidence_score.
Falls back to momentum placeholder if TF missing or insufficient data.
"""
from typing import Optional, List
from agents.models import MLSignal
from utils.logger import logger

SEQ_LEN = 20
MIN_POINTS = SEQ_LEN + 15
LSTM_UNITS = 32
EPOCHS = 10
BATCH_SIZE = 16


def _build_return_sequences(closes: List[float], seq_len: int):
    """Build (X, y) from log returns. X shape (n, seq_len, 1), y = next return."""
    import math
    if len(closes) < seq_len + 2:
        return None, None
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] and closes[i - 1] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
        else:
            returns.append(0.0)
    if len(returns) < seq_len + 1:
        return None, None
    X, y = [], []
    for i in range(seq_len, len(returns)):
        X.append(returns[i - seq_len : i])
        y.append(returns[i])
    import numpy as np
    X = np.array(X, dtype=np.float32).reshape(-1, seq_len, 1)
    y = np.array(y, dtype=np.float32)
    return X, y


def _train_and_predict_lstm(closes: List[float]) -> Optional[tuple]:
    """Train small LSTM on returns, predict next return. Returns (pred_return, current_price) or None."""
    try:
        import numpy as np
        from tensorflow import keras
        from tensorflow.keras import layers
    except ImportError:
        return None
    X, y = _build_return_sequences(closes, SEQ_LEN)
    if X is None or len(X) < 5:
        return None
    model = keras.Sequential([
        layers.Input(shape=(SEQ_LEN, 1)),
        layers.LSTM(LSTM_UNITS, activation="tanh"),
        layers.Dense(1),
    ])
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3), loss="mse")
    model.fit(X, y, epochs=EPOCHS, batch_size=min(BATCH_SIZE, len(X)), verbose=0)
    last_seq = X[-1:].astype(np.float32)
    pred_return = float(model.predict(last_seq, verbose=0)[0, 0])
    current = closes[-1] if closes else 0
    return (pred_return, current)


class LSTMPredictor:
    """
    Uses a real LSTM when TensorFlow is available and history is long enough;
    otherwise falls back to momentum-based placeholder.
    """

    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days

    def predict(self, symbol: str, history_close_series=None) -> MLSignal:
        if history_close_series is None or len(history_close_series) < 2:
            return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="LSTM")

        closes = list(history_close_series)
        if len(closes) >= MIN_POINTS:
            result = _train_and_predict_lstm(closes)
            if result is not None:
                pred_return, current_price = result
                confidence = max(-1.0, min(1.0, pred_return * 10.0))
                pred_delta = pred_return * current_price if current_price else 0
                return MLSignal(
                    confidence_score=confidence,
                    predicted_price_delta=pred_delta,
                    model_name="LSTM",
                )
        recent = closes[-min(self.lookback_days, len(closes)):]
        if len(recent) < 2:
            return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="LSTM")
        start_price = recent[0]
        end_price = recent[-1]
        ret = (end_price - start_price) / start_price if start_price else 0
        confidence = max(-1.0, min(1.0, ret * 5.0))
        pred_delta = ret * end_price if end_price else 0
        return MLSignal(
            confidence_score=confidence,
            predicted_price_delta=pred_delta,
            model_name="LSTM",
        )
