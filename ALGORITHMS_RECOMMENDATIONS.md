# Trading Agent: Current Algorithms & Recommendations

## Current Stack

| Component | Role | Implementation |
|-----------|------|----------------|
| **LSTM** (40% weight) | Price trend / sequence | Placeholder: simple momentum (lookback 20 days). No trained LSTM yet. |
| **XGBoost** (20% weight) | ML signal | Placeholder: mean-reversion vs 10-day MA. No trained XGBoost yet. |
| **Sentiment LLM** (30% weight) | News/headlines | OpenRouter: headlines → polarity + confidence. |
| **Macro LLM** (10% weight) | Macro context | OpenRouter: macro description → stance + confidence. |
| **Orchestrator** | Combine signals | Weighted composite → Buy/Sell/Hold + Kelly-style position size. |
| **Guardrails** | Risk | Hold if volatility > 50% or spread too high. |

---

## Recommendations

### 1. **Replace LSTM placeholder with a real model**
- **Current:** Momentum over 20 days (no LSTM).
- **Better:** Train a small LSTM (or GRU/Transformer) on historical closes/returns per symbol (or a shared model with symbol embedding). Use it for next-step or short-horizon return prediction. Libraries: TensorFlow/Keras or PyTorch; keep inference fast (e.g. load once per process).

### 2. **Replace XGBoost placeholder with a real model**
- **Current:** Simple mean-reversion vs 10-day MA.
- **Better:** Train XGBoost (or LightGBM/CatBoost) on features: returns (1d, 5d, 20d), volatility, volume change, RSI, distance to MA. Target: next-day or next-period return/direction. Retrain periodically (e.g. weekly) on recent data.

### 3. **Add technical / statistical signals**
- **RSI, MACD, Bollinger distance:** Easy to add as extra inputs to the ensemble or as a separate “Technical” weight (e.g. 10%).
- **Volatility regime:** Use realized vol (e.g. 8h or daily) to adjust position size or disable buys in very high vol.

### 4. **Improve position sizing**
- **Current:** Simplified Kelly (kelly_fraction * composite * confidence).
- **Better:** Full Kelly or half-Kelly with estimated win rate and payoff from backtests; cap max position (e.g. 20% per name) and reduce size when volatility is high.

### 5. **Sentiment & macro**
- **Current:** Stub headlines and generic macro text.
- **Better:** Real news API (e.g. NewsAPI, Alpha Vantage News) and macro series (rates, CPI, employment) fed to the LLM for richer Sentiment/Macro signals.

### 6. **Alternative / additional models**
- **Random Forest / Extra Trees:** Good baseline for tabular features (returns, vol, volume); often on par with XGBoost with less tuning.
- **Transformer / TFT:** For longer sequences and multi-horizon forecasts if you have enough data and compute.
- **LightGBM:** Faster training than XGBoost, similar accuracy; good for many symbols and frequent retrains.

### 7. **Backtesting**
- Run the ensemble (with placeholders or new models) on historical data; measure Sharpe, max drawdown, win rate. Use the same guardrails and position sizing as in live/paper to avoid overfitting.

---

## Summary

- **Highest impact:** Replace LSTM and XGBoost placeholders with trained models on real features and targets.
- **Quick wins:** Add RSI/MACD (or similar) and real news/macro inputs to the LLM.
- **Risk:** Improve position sizing and volatility-aware caps; keep guardrails.
