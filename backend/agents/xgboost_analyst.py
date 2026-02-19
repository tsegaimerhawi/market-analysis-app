"""
XGBoost analyst: trains on features (returns 1d/5d/20d, volatility, RSI, distance to MA),
target = next-day return direction. Predicts confidence for the ensemble.
Falls back to mean-reversion placeholder if XGBoost missing or insufficient data.
"""
from typing import List, Optional
from agents.models import MLSignal
from utils.logger import logger

FEATURE_LOOKBACK = 25
RSI_PERIOD = 14


def _returns(closes: List[float]) -> List[float]:
    out = []
    for i in range(1, len(closes)):
        if closes[i - 1] and closes[i - 1] > 0:
            out.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            out.append(0.0)
    return out


def _rsi_at(closes: List[float], end_idx: int, period: int = RSI_PERIOD) -> float:
    if end_idx < period:
        return 50.0
    gains, losses = [], []
    for i in range(end_idx - period, end_idx):
        if i <= 0 or i >= len(closes):
            continue
        chg = closes[i] - closes[i - 1]
        gains.append(chg if chg > 0 else 0.0)
        losses.append(-chg if chg < 0 else 0.0)
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _build_features_and_targets(closes: List[float]) -> Optional[tuple]:
    """Returns (X_list, y_list) for training: X = list of feature vectors, y = 1 or -1 (next-day direction)."""
    if len(closes) < FEATURE_LOOKBACK + 2:
        return None
    rets = _returns(closes)
    if len(rets) < FEATURE_LOOKBACK + 1:
        return None
    X_list, y_list = [], []
    for i in range(FEATURE_LOOKBACK, len(rets)):
        r1 = rets[i - 1] if i >= 1 else 0
        r5 = (closes[i] / closes[i - 5] - 1.0) if i >= 5 else 0
        r20 = (closes[i] / closes[i - 20] - 1.0) if i >= 20 else 0
        window = rets[i - 20 : i] if i >= 20 else rets[:i]
        vol = (sum((x - sum(window) / len(window)) ** 2 for x in window) / len(window)) ** 0.5 if window else 0
        rsi = _rsi_at(closes, i)
        ma20 = sum(closes[i - 20 : i]) / 20 if i >= 20 else closes[i]
        dist_ma = (closes[i] - ma20) / ma20 if ma20 else 0
        X_list.append([r1, r5, r20, vol, rsi / 100.0 - 0.5, dist_ma])
        next_ret = rets[i] if i < len(rets) else 0
        y_list.append(1 if next_ret > 0 else -1)
    return (X_list, y_list)


def _train_and_predict_xgb(closes: List[float]) -> Optional[float]:
    """Train XGBoost on features, predict confidence for last row. Returns confidence in [-1,1] or None."""
    try:
        import xgboost as xgb
        import numpy as np
    except ImportError:
        return None
    data = _build_features_and_targets(closes)
    if data is None:
        return None
    X_train_list, y_train_list = data
    if len(X_train_list) < 10:
        return None
    
    # To predict the TRUE future return (tomorrow), we need a feature vector built from the absolute latest data.
    # _build_features_and_targets ends at the last return. We need one more step.
    rets = _returns(closes)
    i = len(rets) # Pointing one past the end of returns to use everything for features
    
    r1 = rets[i - 1] if i >= 1 else 0
    r5 = (closes[i] / closes[i - 5] - 1.0) if i >= 5 else 0
    r20 = (closes[i] / closes[i - 20] - 1.0) if i >= 20 else 0
    window = rets[i - 20 : i] if i >= 20 else rets[:i]
    vol = (sum((x - sum(window) / len(window)) ** 2 for x in window) / len(window)) ** 0.5 if window else 0
    rsi = _rsi_at(closes, i)
    ma20 = sum(closes[i - 20 : i]) / 20 if i >= 20 else closes[i]
    dist_ma = (closes[i] - ma20) / ma20 if ma20 else 0
    X_future = np.array([[r1, r5, r20, vol, rsi / 100.0 - 0.5, dist_ma]], dtype=np.float32)

    X = np.array(X_train_list, dtype=np.float32)
    y = np.array(y_train_list, dtype=np.int32)
    
    try:
        model = xgb.XGBClassifier(n_estimators=50, max_depth=4, eval_metric="logloss", verbosity=0)
    except TypeError:
        model = xgb.XGBClassifier(n_estimators=50, max_depth=4, verbosity=0)
    
    model.fit(X, y)
    pred = model.predict(X_future)[0]
    proba = model.predict_proba(X_future)
    if proba.shape[1] == 2:
        confidence = (float(proba[0, 1]) - 0.5) * 2
    else:
        confidence = 1.0 if pred == 1 else -1.0
    return max(-1.0, min(1.0, confidence))


class XGBoostAnalyst:
    """
    Uses a real XGBoost model on returns, vol, RSI, MA distance when data is sufficient;
    otherwise mean-reversion placeholder.
    """

    def __init__(self, window: int = 10):
        self.window = window

    def predict(self, symbol: str, history_close_series=None) -> MLSignal:
        if history_close_series is None or len(history_close_series) < self.window + 1:
            return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="XGBoost")

        closes = list(history_close_series)
        conf = _train_and_predict_xgb(closes)
        if conf is not None:
            current = closes[-1] if closes else 0
            return MLSignal(
                confidence_score=conf,
                predicted_price_delta=conf * current * 0.01 if current else 0,
                model_name="XGBoost",
            )
        recent = closes[-self.window - 1:]
        current = recent[-1]
        ma = sum(recent[:-1]) / (len(recent) - 1) if len(recent) > 1 else current
        if ma == 0:
            return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="XGBoost")
        deviation = (current - ma) / ma
        confidence = max(-1.0, min(1.0, -deviation * 3.0))
        return MLSignal(
            confidence_score=confidence,
            predicted_price_delta=(ma - current) * 0.1,
            model_name="XGBoost",
        )
