"""
Local DL layer: LSTM-style predictor placeholder.
Outputs confidence_score (-1.0 to 1.0) and predicted_price_delta for the ensemble.
In production this would load a trained PyTorch/TensorFlow LSTM.
"""
from typing import Optional
from agents.models import MLSignal
from utils.logger import logger


class LSTMPredictor:
    """
    Placeholder for an LSTM model. Uses simple momentum from recent closes
    when no trained model is available; replace with real LSTM inference for production.
    """

    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days
        self._model_loaded = False  # Set True when you load a real model

    def predict(self, symbol: str, history_close_series=None) -> MLSignal:
        """
        Produce a DL signal. If history_close_series is provided (array-like of closes),
        use a simple momentum rule as placeholder. Otherwise return neutral.
        """
        if history_close_series is None or len(history_close_series) < 2:
            logger.debug("LSTMPredictor: no history, returning neutral")
            return MLSignal(
                confidence_score=0.0,
                predicted_price_delta=0.0,
                model_name="LSTM",
            )

        try:
            # Placeholder: momentum-based signal (positive momentum -> positive confidence)
            closes = list(history_close_series)
            recent = closes[-min(self.lookback_days, len(closes)):]
            if len(recent) < 2:
                return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="LSTM")
            start_price = recent[0]
            end_price = recent[-1]
            ret = (end_price - start_price) / start_price if start_price else 0
            # Clamp to roughly -1..1 and scale
            confidence = max(-1.0, min(1.0, ret * 5.0))  # scale momentum
            pred_delta = ret * end_price if end_price else 0  # simple expected $ change
            return MLSignal(
                confidence_score=confidence,
                predicted_price_delta=pred_delta,
                model_name="LSTM",
            )
        except Exception as e:
            logger.exception("LSTMPredictor predict failed: %s", e)
            return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="LSTM")
