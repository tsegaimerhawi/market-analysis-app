# Stock Market Agent — Improvement Ideas (Paper Trading)

This document summarizes a full code review of your buy/sell agent and suggests concrete improvements, ordered by impact and effort.

---

## 1. Risk & Execution

### 1.1 Limit orders only checked on portfolio load
**Current:** Pending limit orders are executed only when someone calls `GET /api/portfolio` (`_check_pending_limit_orders()`).

**Problem:** If the agent or user places limit orders but no one opens the Portfolio page, those orders never get a chance to fill.

**Improvement:** Run the same limit-order check inside the agent cycle (e.g. at the start of `run_agent_cycle()` in `agent_runner.py`), and/or from a small scheduled task (e.g. every 5 minutes) so limits can fill even when the UI is closed.

---

### 1.2 Reset paper account leaves limit orders and agent logs
**Current:** `reset_paper_account()` in `db.py` clears `account`, `portfolio`, and `orders` but not `limit_orders`, `agent_reasoning`, or `agent_history`.

**Problem:** After a reset, old limit orders can still exist and execute on next portfolio load; old reasoning/history can confuse debugging.

**Improvement:** Either:
- Clear `limit_orders` (and optionally `agent_reasoning` / `agent_history`) when resetting the paper account, or
- Add an optional query/body flag, e.g. `clear_limit_orders=true` and `clear_agent_logs=true`, so the user can choose.

---

### 1.3 No bid/ask spread in guardrails
**Current:** `TradeOrchestrator.check_guardrails()` accepts `bid_ask_spread_pct` but the agent always passes `None` (`agent_runner.py` and `backtest_runner.py`).

**Improvement:** If your data source (e.g. yfinance or a future broker API) provides bid/ask, compute spread and pass it into `decide()`. Then the guardrail can block trades when spread is too wide (e.g. illiquid names).

---

### 1.4 Concentration limit (max % per symbol)
**Current:** Position size is capped as a fraction of **cash** per trade (e.g. 20% max), but there is no cap on how much of **total portfolio** can be in one symbol.

**Improvement:** Before buying, compute `position_value / (cash + total_positions_value)`. If adding this trade would push the symbol above a cap (e.g. 25% of portfolio), reduce size or skip the buy. This avoids over-concentration in one name.

---

### 1.5 Cooldown / overtrading
**Current:** The agent can decide Buy in every 30-minute cycle for the same symbol, so it might keep adding to a position every cycle.

**Improvement:** Optional “cooldown”: e.g. no new buy in the same symbol for N hours (or N cycles) after the last buy. Store last-buy time per symbol (e.g. in DB or in-memory) and skip or reduce size when inside the cooldown window.

---

## 2. Backtest Realism

### 2.1 Look-ahead bias: current news/macro for historical days
**Current:** In `backtest_runner.py`, for each historical day you call `get_headlines(symbol)` and `get_macro_indicators()`, which return **current** news and macro data, not data as of that day.

**Problem:** Backtest results are overstated because the model “sees” future news/macro on past dates.

**Improvement:** For backtest, pass a “backtest mode” flag and use **stub** sentiment/macro (e.g. neutral polarity and stance, fixed confidence) so that only price-based and technical signals drive the backtest. Optionally later integrate a proper point-in-time news/macro source for backtests.

---

### 2.2 Transaction costs and slippage
**Current:** Backtest assumes fills at exactly `current_price` with no costs.

**Improvement:** Subtract a small commission per trade (e.g. $1 or 0.1%) and optionally apply slippage (e.g. buy at `current_price * 1.001`, sell at `current_price * 0.999`) so backtest metrics (Sharpe, drawdown, win rate) are more realistic.

---

## 3. Models & Signals

### 3.1 LSTM: train once per symbol (or cache)
**Current:** In `lstm_predictor.py`, `_train_and_predict_lstm()` is called on every `decide()` with the latest history, so the LSTM is retrained from scratch every time (e.g. every 30 min for every symbol).

**Problems:** Slow and expensive; can overfit to the most recent window.

**Improvement:** Train less frequently (e.g. daily or weekly) and cache the model per symbol (or a shared model with symbol embedding). At inference time, only run a forward pass. Optionally keep a small fine-tune step on very recent bars.

---

### 3.2 XGBoost: same idea
**Current:** XGBoost is retrained on every `decide()` in `xgboost_analyst.py`.

**Improvement:** Same as LSTM: train periodically (e.g. weekly), cache the model, and only run prediction in the hot path. Retrain when new data is available or on a schedule.

---

### 3.3 Ensemble weights and confidence floor
**Current:** Weights and confidence floor (0.18) are hardcoded in `trade_orchestrator.py`.

**Improvement:** Make them configurable (e.g. via env vars or agent_settings in DB): `AGENT_WEIGHT_LSTM`, `AGENT_WEIGHT_XGBOOST`, …, `AGENT_CONFIDENCE_FLOOR`. That allows tuning without code changes and A/B tests in paper trading.

---

## 4. Data & APIs

### 4.1 Macro data is minimal
**Current:** `macro_fetcher.py` only uses Fed funds rate (Alpha Vantage) when `MACRO_API_KEY` is set.

**Improvement:** Add CPI, unemployment, or other series (e.g. from FRED or Alpha Vantage) and include them in the description sent to the Macro LLM so the macro signal is richer and more stable.

---

### 4.2 Rate limiting and latency (LLM + news)
**Current:** Each agent cycle runs the full ensemble for every symbol in the universe (watchlist + normal + volatile). For each symbol you call OpenRouter (sentiment + macro) and possibly NewsAPI. With many symbols this can hit rate limits and make the cycle very slow.

**Improvement:**
- Cache sentiment/macro per symbol with a TTL (e.g. 30–60 minutes) so you don’t call the LLM for the same symbol every cycle.
- Optionally batch headlines for multiple symbols into one LLM call (e.g. “For each of AAPL, MSFT, … output sentiment”) to reduce API calls.
- Add a simple rate limiter (e.g. max N OpenRouter requests per minute) and back off or skip symbols if over limit.

---

### 4.3 News headline window
**Current:** News fetcher uses last 2 days of headlines.

**Improvement:** Make the window configurable (e.g. 1–3 days) and consider caching results per symbol with TTL to reduce NewsAPI usage and speed up cycles.

---

## 5. Operations & Robustness

### 5.1 Agent cycle timeout and partial results
**Current:** If one symbol throws (e.g. bad data or API error), the cycle logs and continues, but a long-running cycle could block the thread.

**Improvement:** Add a per-symbol timeout (e.g. 30 seconds) and catch timeouts so one slow symbol doesn’t stall the whole cycle. Optionally cap total cycle time and process remaining symbols in the next cycle.

---

### 5.2 Circuit breaker (optional)
**Current:** Agent keeps trading according to the model regardless of recent performance.

**Improvement:** Optional “circuit breaker”: e.g. if the paper account has drawdown > X% from peak or N consecutive losing trades, automatically set agent to “pause” (or reduce position sizes) until the user resets or re-enables. Store peak equity and recent trade outcomes in DB or memory.

---

### 5.3 Structured logging for reasoning
**Current:** Reasoning is stored in `agent_reasoning` with free-form `message` and `data`.

**Improvement:** Use a consistent structure for `data` (e.g. `lstm_score`, `xgb_score`, `composite`, `action`) so you can query and analyze which signals led to wins/losses and tune weights or thresholds.

---

## 6. Quick Wins (low effort)

| Item | Where | Change |
|------|--------|--------|
| Run limit-order check in agent cycle | `agent_runner.py` | Call `_check_pending_limit_orders()` at start of `run_agent_cycle()` (import from main or db/service). |
| Clear limit orders on paper reset | `db.py` | In `reset_paper_account()`, add `DELETE FROM limit_orders`. |
| Backtest without live news/macro | `backtest_runner.py` | If `backtest_mode=True`, pass empty or stub headlines/macro into `decide()`. |
| Configurable confidence floor | `trade_orchestrator.py` | Read `AGENT_CONFIDENCE_FLOOR` from env (default 0.18). |
| Pass spread when available | `agent_runner.py` | If `get_quote()` or future API returns bid/ask, compute `spread_pct` and pass to `decide()`. |

---

## 7. Summary Table

| Area | Priority | Effort | Impact |
|------|----------|--------|--------|
| Limit orders checked in agent cycle | High | Low | Prevents “stale” limit orders |
| Backtest: no look-ahead (stub news/macro) | High | Low | Realistic backtest metrics |
| Reset paper: clear limit orders | Medium | Low | Cleaner state after reset |
| LSTM/XGBoost cache, train less often | High | Medium | Speed + stability |
| Concentration limit per symbol | Medium | Medium | Risk control |
| Sentiment/macro cache + rate limit | Medium | Medium | Fewer API errors, faster cycles |
| Transaction costs in backtest | Medium | Low | More realistic PnL |
| Bid/ask spread guardrail | Medium | Low–Medium | Depends on data source |
| Cooldown per symbol | Low | Medium | Fewer redundant buys |
| Circuit breaker | Low | Medium | Extra safety in paper/live |

Implementing the quick wins and the high-priority risk/backtest items will make paper trading more reliable and backtests more trustworthy, without changing your core ensemble logic.
