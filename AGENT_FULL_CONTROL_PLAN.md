# Plan: Agent 100% Control Mode

When this mode is **on**, the agent’s ensemble output is the only source of trading decisions. No system guardrails, filters, or rule-based overrides will force Hold or change position size. Exits (when to sell) are also fully decided by the agent (no automatic stop-loss/take-profit).

---

## What Overrides the Agent Today

| # | Location | What overrides the agent |
|---|----------|---------------------------|
| 1 | **Orchestrator** | **Hard guardrails**: if volatility &gt; 50% or spread too high → forced **Hold**. |
| 2 | **Orchestrator** | **Confidence floor**: if `avg_confidence < 0.18` → forced **Hold**. |
| 3 | **Orchestrator** | **Macro/sentiment dampening**: composite is multiplied by 0.4 or 0.5 in some cases (buy into headwinds / sell into tailwinds). |
| 4 | **Orchestrator** | **Agreement rule**: need `agree_count >= 2` and `agreement == "bull"` or `"bear"` to get Buy/Sell; otherwise **Hold**. |
| 5 | **Orchestrator** | **Position caps**: `max_position_cap` (e.g. 20%), Kelly fraction, volatility scaling, and `size_mult` (from agree_count and trend_align) reduce position size. |
| 6 | **Agent runner** | **Stop-loss**: if position P&amp;L ≤ -stop_loss_pct → **automatic full sell** (agent did not decide). |
| 7 | **Agent runner** | **Take-profit**: if position P&amp;L ≥ take_profit_pct → **automatic full sell** (agent did not decide). |
| 8 | **Agent runner** | **Volatile-only cap**: for symbols only in the volatile list (not watchlist), position size capped at **15%** of cash. |
| 9 | **Agent runner** | When volatile is on and user didn’t set stop-loss, **default 5% stop-loss** is applied. |

---

## Proposed Design: Single Setting “Full control”

- **New setting**: `agent_full_control` (boolean) in `agent_settings` (DB), plus optional env `AGENT_FULL_CONTROL=1`.
- **When `agent_full_control` is true:**
  - Orchestrator does **not** apply any of the overrides above (1–5).
  - Agent runner does **not** apply stop-loss, take-profit, or volatile-only cap (6–9); and does **not** inject a default stop-loss when volatile is on.

Concretely:

- **Orchestrator (full control = true):**
  - Skip `check_guardrails()` (or treat as “never trigger”): never force Hold for volatility/spread.
  - Skip confidence floor: do not force Hold for low confidence.
  - Skip macro/sentiment dampening: use raw composite, no 0.4/0.5 multipliers.
  - Skip agreement requirement: map composite directly to Buy/Sell/Hold (e.g. composite ≥ small threshold → Buy, ≤ negative threshold → Sell), no minimum `agree_count`.
  - Position size: use composite and confidence only, with a single high cap (e.g. 0.5 or 1.0) and no volatility scaling / no size_mult from agreement or trend (or make cap configurable).

- **Agent runner (full control = true):**
  - Do **not** run stop-loss or take-profit logic: only sell when the orchestrator returns **Sell** (and then use `decision.position_size` as now).
  - Do **not** cap position size for volatile-only symbols: use `decision.position_size` as-is (optionally with one global max, e.g. 50% of cash, to avoid a single bug wiping the account).
  - Do **not** set default stop-loss when volatile is on.

- **When `agent_full_control` is false:**  
  Current behavior unchanged (all guardrails, filters, stop-loss, take-profit, volatile cap, default stop-loss when volatile).

---

## Implementation Steps (for your approval)

1. **DB & API**
   - Add `agent_full_control` to `agent_settings`: `get_agent_full_control()`, `set_agent_full_control(bool)`.
   - Expose in `GET/POST /api/agent/status`: return and accept `full_control` (boolean).

2. **Orchestrator**
   - Add parameter `full_control: bool = False` to `decide()` (or read from a small context object passed from runner).
   - When `full_control`:
     - Skip guardrails (do not call `check_guardrails` for forcing Hold; optionally still log a warning).
     - Skip confidence floor (remove the `avg_confidence < 0.18` Hold).
     - Skip macro/sentiment dampening (do not multiply composite by 0.4/0.5).
     - Action: `composite >= threshold_buy → Buy`, `composite <= threshold_sell → Sell`, else Hold; no `agree_count` or `agreement` requirement.
     - Position size: from composite and confidence only, with one configurable max (e.g. 0.5) and no volatility scaling / no size_mult from agreement or trend.

3. **Agent runner**
   - Read `get_agent_full_control()` at start of cycle.
   - When `full_control` is true:
     - Do not run stop-loss or take-profit checks; do not apply default stop-loss for volatile.
     - Do not cap position size for volatile-only symbols (use `decision.position_size` as returned).
   - When `full_control` is false: keep current behavior (stop-loss, take-profit, volatile cap, default stop-loss when volatile).

4. **Backtest**
   - Optional: add a `full_control` (or backtest-specific) flag to the backtest runner so backtests can run in “agent full control” mode for consistency with paper trading when that mode is on.

5. **Frontend (optional)**
   - In the agent control UI, add a checkbox or toggle for “Full control (no guardrails, no stop-loss/take-profit)” that sets `full_control` via the existing status API.

---

## Risks When Full Control Is On

- **No guardrails:** Trades can occur in very high volatility or wide spread; position size can be large.
- **No stop-loss / take-profit:** Exits are only when the agent outputs Sell; drawdowns can be larger.
- **No volatile-only cap:** The agent can put as much (up to the single cap) into volatile names as it wants.

So “100% control” is appropriate for experimentation and paper trading; for real money you’d likely turn it off or add your own limits outside the agent.

---

## Summary

| Step | What |
|------|------|
| 1 | Add `agent_full_control` setting (DB + API). |
| 2 | In orchestrator, when full control: no guardrails, no confidence floor, no dampening, no agreement rule; direct composite → action; simple position size with one high cap. |
| 3 | In agent runner, when full control: no stop-loss, no take-profit, no volatile-only cap, no default stop-loss for volatile. |
| 4 | (Optional) Backtest and frontend support for full control. |

If you confirm this plan (or specify changes), the next step is to implement steps 1–3 in code.
