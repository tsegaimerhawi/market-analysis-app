"""
Technical indicators: RSI, MACD, Bollinger %B.
Outputs a single MLSignal for the ensemble (Technical weight, e.g. 10%).
"""
from typing import List, Optional
from agents.models import MLSignal
from utils.logger import logger

RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2.0


def _rsi(closes: List[float], period: int = RSI_PERIOD) -> Optional[float]:
    """RSI (0-100). Returns None if insufficient data."""
    if not closes or len(closes) < period + 1:
        return None
    closes = list(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        chg = closes[i] - closes[i - 1]
        gains.append(chg if chg > 0 else 0.0)
        losses.append(-chg if chg < 0 else 0.0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _macd_signal(closes: List[float], fast: int = MACD_FAST, slow: int = MACD_SLOW, signal: int = MACD_SIGNAL) -> Optional[float]:
    """MACD line - signal line. Positive = bullish. Returns None if insufficient data."""
    if not closes or len(closes) < slow + signal:
        return None
    def ema(data: List[float], period: int) -> List[float]:
        out = []
        mult = 2.0 / (period + 1)
        for i, v in enumerate(data):
            if i == 0:
                out.append(float(v))
            else:
                out.append((v - out[-1]) * mult + out[-1])
        return out
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
    if len(macd_line) < signal:
        return None
    signal_line = ema(macd_line, signal)
    return macd_line[-1] - signal_line[-1]


def _bollinger_pct_b(closes: List[float], period: int = BOLLINGER_PERIOD, num_std: float = BOLLINGER_STD) -> Optional[float]:
    """Bollinger %B: (price - lower) / (upper - lower). >1 overbought, <0 oversold. Returns None if insufficient data."""
    if not closes or len(closes) < period:
        return None
    recent = closes[-period:]
    ma = sum(recent) / period
    var = sum((x - ma) ** 2 for x in recent) / period
    std = var ** 0.5 if var > 0 else 0
    if std == 0:
        return 0.5
    upper = ma + num_std * std
    lower = ma - num_std * std
    price = closes[-1]
    if upper == lower:
        return 0.5
    return (price - lower) / (upper - lower)


class TechnicalAnalyst:
    """Combines RSI, MACD, Bollinger %B into one signal (-1 to 1) for the ensemble."""

    def predict(self, symbol: str, history_close_series=None) -> MLSignal:
        if history_close_series is None or len(history_close_series) < max(RSI_PERIOD + 1, MACD_SLOW + MACD_SIGNAL, BOLLINGER_PERIOD):
            return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="Technical")
        try:
            closes = list(history_close_series)
            rsi = _rsi(closes)
            macd = _macd_signal(closes)
            pct_b = _bollinger_pct_b(closes)
            # Normalize to -1..1 and combine
            # RSI: 50 neutral, <30 oversold (bullish), >70 overbought (bearish)
            rsi_score = 0.0
            if rsi is not None:
                rsi_score = (50.0 - rsi) / 50.0  # -1 at RSI 100, +1 at RSI 0
                rsi_score = max(-1.0, min(1.0, rsi_score))
            macd_score = 0.0
            if macd is not None and closes[-1]:
                macd_norm = macd / closes[-1] * 100
                macd_score = max(-1.0, min(1.0, macd_norm * 5))
            # %B: >1 overbought (bearish), <0 oversold (bullish)
            bb_score = 0.0
            if pct_b is not None:
                bb_score = (0.5 - pct_b) * 2
                bb_score = max(-1.0, min(1.0, bb_score))
            # Equal weight blend
            composite = (rsi_score + macd_score + bb_score) / 3.0
            composite = max(-1.0, min(1.0, composite))
            return MLSignal(
                confidence_score=composite,
                predicted_price_delta=composite * (closes[-1] * 0.01) if closes else 0.0,
                model_name="Technical",
            )
        except Exception as e:
            logger.debug("TechnicalAnalyst failed %s: %s", symbol, e)
            return MLSignal(confidence_score=0.0, predicted_price_delta=0.0, model_name="Technical")
