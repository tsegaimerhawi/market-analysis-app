"""
LSTM predictor: uses a small Keras LSTM on recent price history when available.
Trains on last N days of returns, predicts next-step return -> confidence_score.
Falls back to momentum placeholder if TF missing or insufficient data.
"""
from typing import List, Optional

from agents.models import MLSignal

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
    
    # To fix lag bias, we use all but the last return for training, 
    # and use the most recent return sequence (including the last return) for prediction.
    X_all, y_all = _build_return_sequences(closes, SEQ_LEN)
    if X_all is None or len(X_all) < 6:
        return None
    
    # Train on all samples except the very last one if we want to be strict,
    # but actually _build_return_sequences builds windows up to the last known 'y'.
    # If we have returns up to 'today', the last y is 'today's return'.
    # To predict 'tomorrow', we need a feature vector that includes 'today'.
    
    # Current behavior of _build_return_sequences:
    # returns = [r1, r2, ... rN] where rN is (priceN - priceN-1)/priceN-1
    # X = [ [r1...r20], [r2...r21], ... [r(N-20)...r(N-1)] ]
    # y = [ r21, r22, ... rN ]
    # The last X is [r(N-20)...r(N-1)], predicting rN.
    
    # To predict r(N+1), we need X_next = [r(N-19)...rN]
    import math
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] and closes[i - 1] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
        else:
            returns.append(0.0)
    
    X_train = X_all # We can train on everything we have
    y_train = y_all
    
    # New sequence for true future prediction
    next_seq = np.array(returns[-SEQ_LEN:], dtype=np.float32).reshape(1, SEQ_LEN, 1)
    
    model = keras.Sequential([
        layers.Input(shape=(SEQ_LEN, 1)),
        layers.LSTM(LSTM_UNITS, activation="tanh"),
        layers.Dense(1),
    ])
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3), loss="mse")
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=min(BATCH_SIZE, len(X_train)), verbose=0)
    
    pred_return = float(model.predict(next_seq, verbose=0)[0, 0])
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
