"""
The Ensemble "Decider": gathers ML/DL and LLM signals, applies weighted decision matrix,
outputs Buy/Sell/Hold with position_size. Includes hard guardrails (volatility, spread).
"""
import os
from typing import List, Optional, Callable
from agents.models import (
    TradeDecision,
    MLSignal,
    SentimentOutput,
    MacroOutput,
)
from agents.lstm_predictor import LSTMPredictor
from agents.xgboost_analyst import XGBoostAnalyst
from agents.technical_analyst import TechnicalAnalyst
from agents.llm_manager import LLMManager
from utils.logger import logger

# Weights for ensemble (must sum to 1.0)
WEIGHT_LSTM = 0.35
WEIGHT_XGBOOST = 0.15
WEIGHT_TECHNICAL = 0.10
WEIGHT_SENTIMENT = 0.30
WEIGHT_MACRO = 0.10

def _risk_mode() -> str:
    return (os.environ.get("AGENT_RISK_MODE") or "balanced").strip().lower()


class TradeOrchestrator:
    """
    Executive that combines numerical data (ML/DL) and text-derived signals (LLM)
    into a single trade decision with position sizing.
    """

    def __init__(
        self,
        lstm: Optional[LSTMPredictor] = None,
        xgb: Optional[XGBoostAnalyst] = None,
        technical: Optional[TechnicalAnalyst] = None,
        llm: Optional[LLMManager] = None,
        on_reasoning: Optional[Callable[[str, str, dict], None]] = None,
    ):
        self.lstm = lstm or LSTMPredictor()
        self.xgb = xgb or XGBoostAnalyst()
        self.technical = technical or TechnicalAnalyst()
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
        max_position_cap: float = 0.20,
        volatility_annual: Optional[float] = None,
        high_vol_threshold: float = 0.35,
    ) -> float:
        """
        Position size as fraction of capital (0-1). Kelly-inspired, capped at max_position_cap,
        and reduced when volatility is high.
        """
        raw = kelly_fraction * composite_score * confidence
        size = max(0.0, min(1.0, raw))
        size = min(size, max_position_cap)
        if volatility_annual is not None and volatility_annual > high_vol_threshold:
            vol_scale = high_vol_threshold / volatility_annual
            size = size * vol_scale
        return max(0.0, min(max_position_cap, size))

    def decide(
        self,
        symbol: str,
        history_closes: Optional[list] = None,
        headlines: Optional[list] = None,
        macro_indicators: Optional[dict] = None,
        current_price: Optional[float] = None,
        volatility_annual: Optional[float] = None,
        bid_ask_spread_pct: Optional[float] = None,
        full_control: bool = False,
    ) -> TradeDecision:
        """
        Run the full ensemble: LSTM, XGBoost, Sentiment, Macro -> weighted score -> Buy/Sell/Hold + position_size.
        If guardrail triggers (and not full_control), return Hold with guardrail_triggered=True.
        When full_control=True, no guardrails, no confidence floor, no dampening, no agreement rule; composite alone drives action.
        """
        self._log(symbol, "start", f"Running ensemble for {symbol}" + (" (full control)" if full_control else ""), {})

        # 1) Hard guardrails first (skipped when full_control)
        if not full_control:
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
                    weights_used={"lstm": WEIGHT_LSTM, "xgboost": WEIGHT_XGBOOST, "technical": WEIGHT_TECHNICAL, "sentiment": WEIGHT_SENTIMENT, "macro": WEIGHT_MACRO},
                )

        # 2) Local ML/DL and technical signals (numerical)
        lstm_signal = self.lstm.predict(symbol, history_closes)
        self._log(symbol, "lstm", f"LSTM confidence={lstm_signal.confidence_score:.3f}, delta={lstm_signal.predicted_price_delta:.4f}", lstm_signal.model_dump())

        xgb_signal = self.xgb.predict(symbol, history_closes)
        self._log(symbol, "xgboost", f"XGBoost confidence={xgb_signal.confidence_score:.3f}, delta={xgb_signal.predicted_price_delta:.4f}", xgb_signal.model_dump())

        technical_signal = self.technical.predict(symbol, history_closes)
        self._log(symbol, "technical", f"Technical (RSI/MACD/BB) confidence={technical_signal.confidence_score:.3f}", technical_signal.model_dump())

        # 3) LLM agents (text -> structured)
        sentiment = self.llm.get_sentiment(headlines or [], symbol)
        self._log(symbol, "sentiment", f"Sentiment polarity={sentiment.polarity:.3f}, confidence={sentiment.confidence:.2f}", sentiment.model_dump())

        macro = self.llm.get_macro(macro_indicators or {}, symbol)
        self._log(symbol, "macro", f"Macro stance={macro.stance:.3f}, confidence={macro.confidence:.2f}", macro.model_dump())

        # 4) Weighted composite score (-1 to 1)
        composite = (
            WEIGHT_LSTM * lstm_signal.confidence_score
            + WEIGHT_XGBOOST * xgb_signal.confidence_score
            + WEIGHT_TECHNICAL * technical_signal.confidence_score
            + WEIGHT_SENTIMENT * sentiment.polarity * sentiment.confidence
            + WEIGHT_MACRO * macro.stance * macro.confidence
        )
        composite = max(-1.0, min(1.0, composite))
        avg_confidence = (
            lstm_signal.confidence_score ** 2 + xgb_signal.confidence_score ** 2
            + technical_signal.confidence_score ** 2
            + sentiment.confidence + macro.confidence
        ) / 5
        avg_confidence = max(0.0, min(1.0, avg_confidence))

        # 4b) Signal agreement: count how many of 5 signals agree in direction (use 0.05 so weak positives count when sentiment/macro are 0)
        signal_agree_thresh = 0.05
        sig_bull = sum(1 for s in [
            lstm_signal.confidence_score,
            xgb_signal.confidence_score,
            technical_signal.confidence_score,
            sentiment.polarity * sentiment.confidence,
            macro.stance * macro.confidence,
        ] if s > signal_agree_thresh)
        sig_bear = sum(1 for s in [
            lstm_signal.confidence_score,
            xgb_signal.confidence_score,
            technical_signal.confidence_score,
            sentiment.polarity * sentiment.confidence,
            macro.stance * macro.confidence,
        ] if s < -signal_agree_thresh)
        agreement = "bull" if sig_bull > sig_bear else ("bear" if sig_bear > sig_bull else "neutral")
        agree_count = max(sig_bull, sig_bear) if agreement != "neutral" else 0

        # 4c) Short-term trend from price vs 20-day MA (avoid buying into downtrend / selling into uptrend without confirmation)
        trend_align = 1.0
        if history_closes and len(history_closes) >= 21:
            price = float(history_closes[-1])
            ma20 = sum(history_closes[-21:-1]) / 20.0
            if ma20 and ma20 > 0:
                trend_pct = (price - ma20) / ma20  # + = above MA (uptrend), - = below MA (downtrend)
                # Scale: strong downtrend (e.g. -5%) penalizes buy; strong uptrend penalizes sell
                if composite >= 0.1 and trend_pct < -0.03:
                    trend_align = max(0.3, 1.0 + trend_pct)  # reduce buy size in downtrend
                elif composite <= -0.1 and trend_pct > 0.03:
                    trend_align = max(0.3, 1.0 - trend_pct)  # reduce sell size in uptrend

        self._log(symbol, "ensemble", f"Composite={composite:.3f}, confidence={avg_confidence:.3f}, agreement={agreement}({agree_count}/5), trend_align={trend_align:.2f}", {"composite": composite, "sig_bull": sig_bull, "sig_bear": sig_bear})

        # 4d) Full control path: no guardrails, no confidence floor, no dampening, no agreement; composite -> action, simple position size
        # Use lower thresholds so agent can buy when LSTM/XGB/Tech are mildly bullish (sentiment/macro often 0 without API keys)
        FULL_CONTROL_BUY_THRESHOLD = 0.04
        FULL_CONTROL_SELL_THRESHOLD = -0.04
        FULL_CONTROL_MAX_POSITION_CAP = 0.5
        if full_control:
            action = "Buy" if composite >= FULL_CONTROL_BUY_THRESHOLD else ("Sell" if composite <= FULL_CONTROL_SELL_THRESHOLD else "Hold")
            # Position size: composite and confidence only, single cap, no volatility scaling
            raw_size = 0.5 * abs(composite) * (0.3 + 0.7 * avg_confidence) if action != "Hold" else 0.0
            position_size = max(0.0, min(FULL_CONTROL_MAX_POSITION_CAP, raw_size))
            reason = f"[Full control] LSTM={lstm_signal.confidence_score:.2f}, XGB={xgb_signal.confidence_score:.2f}, Tech={technical_signal.confidence_score:.2f}, Sent={sentiment.polarity:.2f}, Macro={macro.stance:.2f} -> composite={composite:.2f}"
            return TradeDecision(
                action=action,
                position_size=position_size,
                confidence=avg_confidence,
                reason=reason,
                guardrail_triggered=False,
                weights_used={"lstm": WEIGHT_LSTM, "xgboost": WEIGHT_XGBOOST, "technical": WEIGHT_TECHNICAL, "sentiment": WEIGHT_SENTIMENT, "macro": WEIGHT_MACRO},
            )

        # 5) Confidence floor: don't act on noise (lowered so agent can trade when sentiment/macro are 0/stub)
        CONFIDENCE_FLOOR = 0.12
        if avg_confidence < CONFIDENCE_FLOOR:
            self._log(symbol, "filter", f"Hold: avg_confidence below floor {CONFIDENCE_FLOOR}", {"avg_confidence": avg_confidence})
            return TradeDecision(
                action="Hold",
                position_size=0.0,
                confidence=avg_confidence,
                reason=f"Hold: low conviction (conf={avg_confidence:.2f}). LSTM={lstm_signal.confidence_score:.2f}, XGB={xgb_signal.confidence_score:.2f}, Tech={technical_signal.confidence_score:.2f}, Sent={sentiment.polarity:.2f}, Macro={macro.stance:.2f}",
                guardrail_triggered=False,
                weights_used={"lstm": WEIGHT_LSTM, "xgboost": WEIGHT_XGBOOST, "technical": WEIGHT_TECHNICAL, "sentiment": WEIGHT_SENTIMENT, "macro": WEIGHT_MACRO},
            )

        # 6) Macro/sentiment veto: only dampen on *strong* headwinds (LLM often returns mildly bearish; don't block every buy)
        sent_effective = sentiment.polarity * sentiment.confidence
        macro_effective = macro.stance * macro.confidence
        if composite >= 0.1:
            if macro_effective < -0.55 or sent_effective < -0.55:
                composite = composite * 0.5
                self._log(symbol, "filter", "Buy dampened: macro or sentiment strongly bearish", {"macro_eff": macro_effective, "sent_eff": sent_effective})
        elif composite <= -0.1:
            if macro_effective > 0.55 and sent_effective > 0.55:
                composite = composite * 0.5
                self._log(symbol, "filter", "Sell dampened: macro and sentiment strongly bullish", {"macro_eff": macro_effective, "sent_eff": sent_effective})

        # 7) Map score to action; require at least 1 agreeing signal (so LLM bearish + one bullish price signal can still buy)
        mode = _risk_mode()
        threshold = 0.08 if mode == "aggressive" else 0.08
        sell_threshold = -0.08 if mode == "aggressive" else -0.10
        min_agree_buy = 1
        min_agree_sell = 1
        if composite >= threshold and agree_count >= min_agree_buy and agreement == "bull":
            action = "Buy"
        elif composite <= sell_threshold and agree_count >= min_agree_sell and agreement == "bear":
            action = "Sell"
        else:
            action = "Hold"

        # 8) Position sizing: scale down when only 2 agree or when trend contradicts
        kelly_fraction = 0.35 if mode == "aggressive" else 0.25
        max_cap = 0.30 if mode == "aggressive" else 0.20
        size_mult = 1.0
        if action != "Hold":
            if agree_count == 2:
                size_mult = 0.6  # weaker conviction
            elif agree_count >= 4:
                size_mult = 1.0  # strong agreement
            else:
                size_mult = 0.8
            size_mult = size_mult * trend_align  # trend filter

        position_size = (
            self.compute_position_size(
                abs(composite),
                avg_confidence,
                kelly_fraction=kelly_fraction,
                max_position_cap=max_cap,
                volatility_annual=volatility_annual,
            ) * size_mult if action != "Hold" else 0.0
        )
        position_size = max(0.0, min(max_cap, position_size))
        # Ensure minimum position size when buying so we don't skip due to rounding
        if action == "Buy" and position_size > 0 and position_size < 0.02:
            position_size = 0.02

        reason = f"LSTM={lstm_signal.confidence_score:.2f}, XGB={xgb_signal.confidence_score:.2f}, Tech={technical_signal.confidence_score:.2f}, Sent={sentiment.polarity:.2f}, Macro={macro.stance:.2f} -> composite={composite:.2f} | agreement={agreement}({agree_count}/5), trend_align={trend_align:.2f}"

        logger.info(
            "Decision %s: %s (composite=%.2f, agree=%s, size=%.2f)",
            symbol, action, composite, agree_count, position_size,
        )
        return TradeDecision(
            action=action,
            position_size=position_size,
            confidence=avg_confidence,
            reason=reason,
            guardrail_triggered=False,
            weights_used={"lstm": WEIGHT_LSTM, "xgboost": WEIGHT_XGBOOST, "technical": WEIGHT_TECHNICAL, "sentiment": WEIGHT_SENTIMENT, "macro": WEIGHT_MACRO},
        )
