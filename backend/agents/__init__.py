"""
Hybrid Multi-Agent Trading System.

Integrates local ML/DL models with OpenRouter LLM agents.
- LSTMPredictor, XGBoostAnalyst: numerical signals (confidence_score, predicted_price_delta)
- LLMManager: Sentiment + Macro agents via OpenRouter
- TradeOrchestrator: weighted ensemble -> Buy/Sell/Hold + position_size, with guardrails
"""

from agents.models import (
    SentimentOutput,
    MacroOutput,
    TradeDecision,
    AgentReasoningStep,
    AgentHistoryEntry,
)
from agents.lstm_predictor import LSTMPredictor
from agents.xgboost_analyst import XGBoostAnalyst
from agents.llm_manager import LLMManager
from agents.trade_orchestrator import TradeOrchestrator

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
