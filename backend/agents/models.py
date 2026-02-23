"""
Pydantic models for agent outputs. Ensures LLMs and orchestrator return strictly valid data.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

# --- LLM Agent outputs (structured) ---

class SentimentOutput(BaseModel):
    """Sentiment agent: polarity from headlines/social."""
    polarity: float = Field(ge=-1.0, le=1.0, description="Sentiment -1 (bearish) to 1 (bullish)")
    summary: str = Field(default="", max_length=500)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MacroOutput(BaseModel):
    """Macro agent: view from economic indicators (CPI, rates)."""
    stance: float = Field(ge=-1.0, le=1.0, description="-1 (bearish) to 1 (bullish) for risk assets")
    summary: str = Field(default="", max_length=500)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


# --- Local ML/DL outputs (used by orchestrator) ---

class MLSignal(BaseModel):
    """Unified signal from LSTM or XGBoost."""
    confidence_score: float = Field(ge=-1.0, le=1.0)
    predicted_price_delta: float = Field(description="Expected price change (e.g. % or absolute)")
    model_name: str = ""


# --- Orchestrator output ---

class TradeDecision(BaseModel):
    """Final ensemble decision with position sizing."""
    action: Literal["Buy", "Sell", "Hold"]
    position_size: float = Field(ge=0.0, le=1.0, description="Fraction of available capital (0-1)")
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(default="")
    guardrail_triggered: bool = Field(default=False, description="True if hard guardrail overrode the AI")
    weights_used: Optional[dict] = None  # e.g. {"lstm": 0.4, "xgboost": 0.2, "sentiment": 0.3, "macro": 0.1}


# --- Logging / API ---

class AgentReasoningStep(BaseModel):
    """One step in the agent's reasoning log (for UI)."""
    step: str
    message: str
    data: Optional[dict] = None
    symbol: Optional[str] = None
    timestamp: Optional[str] = None


class AgentHistoryEntry(BaseModel):
    """One entry in agent action history (decision or executed trade)."""
    symbol: str
    action: Literal["Buy", "Sell", "Hold"]
    position_size: float
    reason: str
    executed: bool = False
    order_id: Optional[int] = None
    guardrail_triggered: bool = False
