"""
Hybrid Multi-Agent Trading System.

Integrates local ML/DL models with OpenRouter LLM agents.
- LSTMPredictor, XGBoostAnalyst: numerical signals (confidence_score, predicted_price_delta)
- LLMManager: Sentiment + Macro agents via OpenRouter
- TradeOrchestrator: weighted ensemble -> Buy/Sell/Hold + position_size, with guardrails
"""

from agents.llm_manager import LLMManager
from agents.lstm_predictor import LSTMPredictor
from agents.models import (
    AgentHistoryEntry,
    AgentReasoningStep,
    MacroOutput,
    SentimentOutput,
    TradeDecision,
)
from agents.trade_orchestrator import TradeOrchestrator
from agents.xgboost_analyst import XGBoostAnalyst

__all__ = [
    "LSTMPredictor",
    "XGBoostAnalyst",
    "LLMManager",
    "TradeOrchestrator",
    "SentimentOutput",
    "MacroOutput",
    "TradeDecision",
    "AgentReasoningStep",
    "AgentHistoryEntry",
]
