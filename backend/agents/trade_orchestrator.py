"""
The Ensemble "Decider": gathers ML/DL and LLM signals, applies weighted decision matrix,
outputs Buy/Sell/Hold with position_size. Includes hard guardrails (volatility, spread).
"""
from typing import List, Optional, Callable
from agents.models import (
    TradeDecision,
    MLSignal,
    SentimentOutput,
    MacroOutput,
)
from agents.lstm_predictor import LSTMPredictor
from agents.xgboost_analyst import XGBoostAnalyst
from agents.llm_manager import LLMManager
from utils.logger import logger

# Weights for ensemble (must sum to 1.0)
WEIGHT_LSTM = 0.40
WEIGHT_XGBOOST = 0.20
WEIGHT_SENTIMENT = 0.30
WEIGHT_MACRO = 0.10


class TradeOrchestrator:
    """
    Executive that combines numerical data (ML/DL) and text-derived signals (LLM)
    into a single trade decision with position sizing.
    """

    def __init__(
        self,
        lstm: Optional[LSTMPredictor] = None,
        xgb: Optional[XGBoostAnalyst] = None,
        llm: Optional[LLMManager] = None,
        on_reasoning: Optional[Callable[[str, str, dict], None]] = None,
    ):
        self.lstm = lstm or LSTMPredictor()
        self.xgb = xgb or XGBoostAnalyst()
        self.llm = llm or LLMManager()
        self.on_reasoning = on_reasoning  # callback(symbol, step, message, data) for logging

    def _log(self, symbol: str, step: str, message: str, data: Optional[dict] = None):
        if self.on_reasoning:
            try:
                self.on_reasoning(symbol, step, message, data or {})
            except Exception as e:
                logger.warning("on_reasoning callback failed: %s", e)

    def check_guardrails(
        self,
        symbol: str,
        current_price: float,
        volatility_annual: Optional[float] = None,
        bid_ask_spread_pct: Optional[float] = None,
        max_volatility: float = 0.5,
        max_spread_pct: float = 0.5,
    ) -> tuple[bool, str]:
        """
        Hard guardrail: override AI if volatility or spread too high.
        Returns (triggered: bool, reason: str).
        """
        if volatility_annual is not None and volatility_annual > max_volatility:
            return True, f"Volatility {volatility_annual:.2%} exceeds max {max_volatility:.0%}"
        if bid_ask_spread_pct is not None and bid_ask_spread_pct > max_spread_pct:
            return True, f"Bid-ask spread {bid_ask_spread_pct:.2%} exceeds max {max_spread_pct:.0%}"
        return False, ""

    def compute_position_size(
        self,
        composite_score: float,
        confidence: float,
        kelly_fraction: float = 0.25,
    ) -> float:
        """
        Position size as fraction of capital (0-1). Uses a simplified Kelly-inspired rule:
        size = kelly_fraction * composite_score * confidence, clamped to [0, 1].
        """
        raw = kelly_fraction * composite_score * confidence
        return max(0.0, min(1.0, raw))

    def decide(
        self,
        symbol: str,
        history_closes: Optional[list] = None,
        headlines: Optional[list] = None,
        macro_indicators: Optional[dict] = None,
        current_price: Optional[float] = None,
        volatility_annual: Optional[float] = None,
        bid_ask_spread_pct: Optional[float] = None,
    ) -> TradeDecision:
        """
        Run the full ensemble: LSTM, XGBoost, Sentiment, Macro -> weighted score -> Buy/Sell/Hold + position_size.
        If guardrail triggers, return Hold with guardrail_triggered=True.
        """
        self._log(symbol, "start", f"Running ensemble for {symbol}", {})

        # 1) Hard guardrails first
        triggered, reason = self.check_guardrails(
            symbol, current_price or 0, volatility_annual, bid_ask_spread_pct
        )
        if triggered:
            self._log(symbol, "guardrail", reason, {"triggered": True})
            return TradeDecision(
                action="Hold",
                position_size=0.0,
                confidence=0.0,
                reason=reason,
                guardrail_triggered=True,
                weights_used={"lstm": WEIGHT_LSTM, "xgboost": WEIGHT_XGBOOST, "sentiment": WEIGHT_SENTIMENT, "macro": WEIGHT_MACRO},
            )

        # 2) Local ML/DL signals (numerical)
        lstm_signal = self.lstm.predict(symbol, history_closes)
        self._log(symbol, "lstm", f"LSTM confidence={lstm_signal.confidence_score:.3f}, delta={lstm_signal.predicted_price_delta:.4f}", lstm_signal.model_dump())

        xgb_signal = self.xgb.predict(symbol, history_closes)
        self._log(symbol, "xgboost", f"XGBoost confidence={xgb_signal.confidence_score:.3f}, delta={xgb_signal.predicted_price_delta:.4f}", xgb_signal.model_dump())

        # 3) LLM agents (text -> structured)
        sentiment = self.llm.get_sentiment(headlines or [], symbol)
        self._log(symbol, "sentiment", f"Sentiment polarity={sentiment.polarity:.3f}, confidence={sentiment.confidence:.2f}", sentiment.model_dump())

        macro = self.llm.get_macro(macro_indicators or {}, symbol)
        self._log(symbol, "macro", f"Macro stance={macro.stance:.3f}, confidence={macro.confidence:.2f}", macro.model_dump())

        # 4) Weighted composite score (-1 to 1)
        composite = (
            WEIGHT_LSTM * lstm_signal.confidence_score
            + WEIGHT_XGBOOST * xgb_signal.confidence_score
            + WEIGHT_SENTIMENT * sentiment.polarity * sentiment.confidence
            + WEIGHT_MACRO * macro.stance * macro.confidence
        )
        composite = max(-1.0, min(1.0, composite))
        avg_confidence = (
            lstm_signal.confidence_score ** 2 + xgb_signal.confidence_score ** 2
            + sentiment.confidence + macro.confidence
        ) / 4
        avg_confidence = max(0.0, min(1.0, avg_confidence))

        self._log(symbol, "ensemble", f"Composite score={composite:.3f}, avg_confidence={avg_confidence:.3f}", {"composite": composite, "weights": {"lstm": WEIGHT_LSTM, "xgboost": WEIGHT_XGBOOST, "sentiment": WEIGHT_SENTIMENT, "macro": WEIGHT_MACRO}})

        # 5) Map score to action
        if composite >= 0.15:
            action = "Buy"
        elif composite <= -0.15:
            action = "Sell"
        else:
            action = "Hold"

        position_size = self.compute_position_size(abs(composite), avg_confidence) if action != "Hold" else 0.0
        reason = f"LSTM={lstm_signal.confidence_score:.2f}, XGB={xgb_signal.confidence_score:.2f}, Sentiment={sentiment.polarity:.2f}, Macro={macro.stance:.2f} -> composite={composite:.2f}"

        return TradeDecision(
            action=action,
            position_size=position_size,
            confidence=avg_confidence,
            reason=reason,
            guardrail_triggered=False,
            weights_used={"lstm": WEIGHT_LSTM, "xgboost": WEIGHT_XGBOOST, "sentiment": WEIGHT_SENTIMENT, "macro": WEIGHT_MACRO},
        )
