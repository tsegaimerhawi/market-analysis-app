"""
OpenRouter LLM layer. Two agents: Sentiment (news/social) and Macro (economic indicators).
Uses OpenAI client with base_url for OpenRouter; structured JSON output for valid Pydantic parsing.
"""
import os
import json
import asyncio
from typing import Optional

from agents.models import SentimentOutput, MacroOutput
from utils.logger import logger

# OpenRouter API key: OPEN_ROUTER_TRADER_API_KEY or OPEN_ROUTER_API_KEY
OPENROUTER_API_KEY = os.environ.get("OPEN_ROUTER_TRADER_API_KEY") or os.environ.get("OPEN_ROUTER_API_KEY")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _get_client():
    """Lazy import of OpenAI client configured for OpenRouter.
    Use explicit httpx.Client() to avoid OpenAI passing deprecated 'proxies' to httpx 0.28+.
    """
    try:
        from openai import OpenAI
        import httpx
    except ImportError as e:
        raise ImportError("openai and httpx required for LLM agents. pip install openai httpx") from e
    # Pass our own client so OpenAI doesn't inject 'proxies' (breaks on httpx 0.28+)
    http_client = httpx.Client()
    return OpenAI(
        base_url=OPENROUTER_BASE,
        api_key=OPENROUTER_API_KEY or "dummy",
        http_client=http_client,
    )


class LLMManager:
    """
    Manages calls to OpenRouter for Sentiment and Macro agents.
    Hand-off: numerical data (prices, indicators) can be passed as context;
    LLMs return text/JSON which we parse into Pydantic models for the orchestrator.
    """

    def __init__(
        self,
        model: str = "openai/gpt-3.5-turbo",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self._api_key = api_key or OPENROUTER_API_KEY
        self._client = None

    def _client_or_none(self):
        if not self._api_key:
            return None
        try:
            if self._client is None:
                self._client = _get_client()
            return self._client
        except Exception as e:
            logger.warning("LLMManager client init failed: %s", e)
            return None

    def get_sentiment(self, headlines: list[str], symbol: str = "") -> SentimentOutput:
        """
        Sentiment agent: analyze headlines/social feeds, return polarity.
        headlines: list of short text snippets (news/social).
        Returns structured SentimentOutput; on API failure returns neutral.
        """
        client = self._client_or_none()
        if not client or not headlines:
            return SentimentOutput(polarity=0.0, summary="No headlines or API key.", confidence=0.0)

        text = "\n".join(headlines[:20])[:3000]  # cap input size
        prompt = f"""You are a financial sentiment analyst. Given these headlines/feeds for {symbol or "the market"}, output a single JSON object with:
- "polarity": number from -1.0 (bearish) to 1.0 (bullish)
- "summary": one short sentence
- "confidence": number from 0 to 1

Headlines:
{text}

Reply with only the JSON object, no markdown."""

        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=256,
            )
            content = (resp.choices[0].message.content or "").strip()
            # Strip markdown code block if present
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
            data = json.loads(content)
            return SentimentOutput(
                polarity=float(data.get("polarity", 0)),
                summary=str(data.get("summary", ""))[:500],
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception as e:
            logger.exception("Sentiment LLM call failed: %s", e)
            return SentimentOutput(polarity=0.0, summary=f"Error: {e}", confidence=0.0)

    def get_macro(self, indicators: dict, symbol: str = "") -> MacroOutput:
        """
        Macro agent: analyze economic indicators (CPI, rates, etc.), return stance for risk assets.
        indicators: e.g. {"cpi": 3.2, "rates": 5.25, "description": "..."}
        Returns structured MacroOutput; on failure returns neutral.
        """
        client = self._client_or_none()
        if not client:
            return MacroOutput(stance=0.0, summary="No API key.", confidence=0.0)

        desc = indicators.get("description") or json.dumps(indicators)[:2500]
        prompt = f"""You are a macro analyst. Given these economic indicators, output a single JSON object with:
- "stance": number from -1.0 (bearish for risk assets) to 1.0 (bullish)
- "summary": one short sentence
- "confidence": number from 0 to 1

Indicators:
{desc}

Reply with only the JSON object, no markdown."""

        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=256,
            )
            content = (resp.choices[0].message.content or "").strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
            data = json.loads(content)
            return MacroOutput(
                stance=float(data.get("stance", 0)),
                summary=str(data.get("summary", ""))[:500],
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception as e:
            logger.exception("Macro LLM call failed: %s", e)
            return MacroOutput(stance=0.0, summary=f"Error: {e}", confidence=0.0)

    async def get_sentiment_async(self, headlines: list[str], symbol: str = "") -> SentimentOutput:
        """Async wrapper: run get_sentiment in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.get_sentiment(headlines, symbol))

    async def get_macro_async(self, indicators: dict, symbol: str = "") -> MacroOutput:
        """Async wrapper: run get_macro in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.get_macro(indicators, symbol))
