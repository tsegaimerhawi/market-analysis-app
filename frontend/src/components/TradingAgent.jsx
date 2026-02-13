import React, { useState, useEffect } from "react";
import axios from "axios";
import { FaRobot, FaCog, FaHistory, FaBrain, FaPlay, FaToggleOn, FaToggleOff, FaChartLine, FaShieldAlt } from "react-icons/fa";
import "./TradingAgent.css";

const API_BASE = "http://localhost:5001";

export default function TradingAgent() {
  const [enabled, setEnabled] = useState(false);
  const [includeVolatile, setIncludeVolatile] = useState(false);
  const [volatileSymbols, setVolatileSymbols] = useState([]);
  const [stopLossPct, setStopLossPct] = useState("");
  const [takeProfitPct, setTakeProfitPct] = useState("");
  const [loading, setLoading] = useState(false);
  const [reasoning, setReasoning] = useState([]);
  const [history, setHistory] = useState([]);
  const [reasoningSymbol, setReasoningSymbol] = useState("");
  const [runNowLoading, setRunNowLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = () => {
    axios.get(`${API_BASE}/api/agent/status`).then((res) => {
      setEnabled(res.data.enabled);
      setIncludeVolatile(!!res.data.include_volatile);
      setStopLossPct(res.data.stop_loss_pct != null ? String(res.data.stop_loss_pct) : "");
      setTakeProfitPct(res.data.take_profit_pct != null ? String(res.data.take_profit_pct) : "");
    }).catch(() => { setEnabled(false); setIncludeVolatile(false); setStopLossPct(""); setTakeProfitPct(""); });
  };

  const loadVolatileSymbols = () => {
    axios.get(`${API_BASE}/api/agent/volatile-symbols`).then((res) => setVolatileSymbols(res.data.symbols || [])).catch(() => setVolatileSymbols([]));
  };

  const loadReasoning = () => {
    const params = { limit: 100 };
    if (reasoningSymbol) params.symbol = reasoningSymbol;
    axios.get(`${API_BASE}/api/agent/reasoning`, { params }).then((res) => setReasoning(res.data.reasoning || [])).catch(() => setReasoning([]));
  };

  const loadHistory = () => {
    axios.get(`${API_BASE}/api/agent/history`, { params: { limit: 50 } }).then((res) => setHistory(res.data.history || [])).catch(() => setHistory([]));
  };

  useEffect(() => {
    loadStatus();
    loadVolatileSymbols();
  }, []);

  useEffect(() => {
    loadReasoning();
    loadHistory();
    const t = setInterval(() => {
      loadReasoning();
      loadHistory();
    }, 10000);
    return () => clearInterval(t);
  }, [reasoningSymbol]);

  const handleToggle = () => {
    setLoading(true);
    setError(null);
    axios
      .post(`${API_BASE}/api/agent/status`, { enabled: !enabled })
      .then((res) => {
        setEnabled(res.data.enabled);
        setIncludeVolatile(!!res.data.include_volatile);
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Failed to update"))
      .finally(() => setLoading(false));
  };

  const handleIncludeVolatileToggle = () => {
    setLoading(true);
    setError(null);
    axios
      .post(`${API_BASE}/api/agent/status`, { include_volatile: !includeVolatile })
      .then((res) => {
        setIncludeVolatile(!!res.data.include_volatile);
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Failed to update"))
      .finally(() => setLoading(false));
  };

  const saveStopLossTakeProfit = () => {
    setLoading(true);
    setError(null);
    const sl = stopLossPct.trim() ? parseFloat(stopLossPct) : null;
    const tp = takeProfitPct.trim() ? parseFloat(takeProfitPct) : null;
    axios
      .post(`${API_BASE}/api/agent/status`, { stop_loss_pct: sl, take_profit_pct: tp })
      .then((res) => {
        setStopLossPct(res.data.stop_loss_pct != null ? String(res.data.stop_loss_pct) : "");
        setTakeProfitPct(res.data.take_profit_pct != null ? String(res.data.take_profit_pct) : "");
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Failed to save"))
      .finally(() => setLoading(false));
  };

  const handleRunNow = () => {
    setRunNowLoading(true);
    setError(null);
    axios
      .post(`${API_BASE}/api/agent/run`)
      .then(() => {
        loadReasoning();
        loadHistory();
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Run failed"))
      .finally(() => setRunNowLoading(false));
  };

  const formatDate = (s) => (s ? new Date(s).toLocaleString() : "—");

  return (
    <div className="trading-agent-page">
      <header className="agent-page-header">
        <h1><FaRobot className="me-2" />Trading Agent</h1>
        <p className="subtitle">
          Hybrid ensemble: LSTM (40%), XGBoost (20%), Sentiment LLM (30%), Macro LLM (10%). Guardrails override on high volatility or wide spread.
        </p>
      </header>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      <section className="agent-control-card card shadow-sm border-0 mb-4">
        <div className="card-body">
          <h5 className="card-title d-flex align-items-center gap-2">
            <FaCog /> Control
          </h5>
          <div className="alert alert-info py-2 mb-3 d-flex align-items-center gap-2" role="alert">
            <FaShieldAlt />
            <span><strong>Paper trading only.</strong> No real money at risk. All trades are simulated.</span>
          </div>
          <div className="d-flex flex-wrap align-items-center gap-3">
            <div className="d-flex align-items-center gap-2">
              <span className="fw-bold">Auto-trading</span>
              <button
                type="button"
                className={`btn btn-sm ${enabled ? "btn-success" : "btn-outline-secondary"}`}
                onClick={handleToggle}
                disabled={loading}
                title={enabled ? "Turn off" : "Turn on"}
              >
                {enabled ? <FaToggleOn size={24} /> : <FaToggleOff size={24} />}
                <span className="ms-1">{enabled ? "On" : "Off"}</span>
              </button>
            </div>
            <div className="d-flex align-items-center gap-2">
              <span className="fw-bold">Volatile stocks</span>
              <button
                type="button"
                className={`btn btn-sm ${includeVolatile ? "btn-warning" : "btn-outline-secondary"}`}
                onClick={handleIncludeVolatileToggle}
                disabled={loading}
                title="Also buy/sell volatile stocks not in your watchlist"
              >
                {includeVolatile ? <FaToggleOn size={24} /> : <FaToggleOff size={24} />}
                <span className="ms-1">{includeVolatile ? "On" : "Off"}</span>
              </button>
            </div>
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={handleRunNow} disabled={runNowLoading}>
              <FaPlay className="me-1" /> {runNowLoading ? "Running…" : "Run cycle now"}
            </button>
          </div>
          <div className="row g-2 align-items-end mt-3">
            <div className="col-auto">
              <label className="form-label small mb-0">Stop-loss %</label>
              <input
                type="number"
                className="form-control form-control-sm"
                style={{ width: 80 }}
                min="0"
                step="0.5"
                placeholder="e.g. 5"
                value={stopLossPct}
                onChange={(e) => setStopLossPct(e.target.value)}
              />
            </div>
            <div className="col-auto">
              <label className="form-label small mb-0">Take-profit %</label>
              <input
                type="number"
                className="form-control form-control-sm"
                style={{ width: 80 }}
                min="0"
                step="0.5"
                placeholder="e.g. 10"
                value={takeProfitPct}
                onChange={(e) => setTakeProfitPct(e.target.value)}
              />
            </div>
            <div className="col-auto">
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={saveStopLossTakeProfit} disabled={loading}>
                <FaShieldAlt className="me-1" /> Save
              </button>
            </div>
          </div>
          <p className="small text-muted mb-0 mt-2">
            When on, the agent runs every 6 hours over your <strong>watchlist</strong> + <strong>Normal symbols</strong> (e.g. AAPL, NVDA, AMZN). Enable <strong>Volatile stocks</strong> to also trade the top 25 from the volatile list (8h algorithm).
          </p>
          <p className="small text-muted mb-0 mt-1">
            <FaShieldAlt className="me-1" /> <strong>Stop-loss</strong>: sell full position if P&amp;L ≤ -X%. <strong>Take-profit</strong>: sell full position if P&amp;L ≥ Y%. Leave blank to disable. Applies to all agent positions.
          </p>
          {includeVolatile && (
            <div className="small mt-2 p-2 rounded bg-warning bg-opacity-10 border border-warning border-opacity-25">
              <strong>Volatile mode safeguards:</strong> If you don&apos;t set a stop-loss, a <strong>5% default stop-loss</strong> is used so losses are limited. Position size for volatile-only symbols is capped at <strong>15% of cash</strong> per buy to reduce risk.
            </div>
          )}
          {includeVolatile && volatileSymbols.length > 0 && (
            <p className="small mb-0 mt-1">
              <FaChartLine className="me-1" /> Current volatile list (8h algo): {volatileSymbols.join(", ")}
            </p>
          )}
        </div>
      </section>

      <section className="agent-reasoning-card card shadow-sm border-0 mb-4">
        <div className="card-body">
          <h5 className="card-title d-flex align-items-center gap-2">
            <FaBrain /> Reasoning
          </h5>
          <div className="mb-3">
            <label className="form-label small">Filter by symbol</label>
            <input
              type="text"
              className="form-control form-control-sm w-auto text-uppercase"
              placeholder="e.g. AAPL (leave empty for all)"
              value={reasoningSymbol}
              onChange={(e) => setReasoningSymbol(e.target.value)}
            />
          </div>
          <div className="reasoning-list">
            {reasoning.length === 0 ? (
              <p className="text-muted small mb-0">No reasoning steps yet. Turn the agent on or run a cycle.</p>
            ) : (
              reasoning.map((r) => (
                <div key={r.id} className="reasoning-item">
                  <div className="d-flex justify-content-between align-items-start flex-wrap gap-2">
                    <span className="reasoning-meta">
                      {formatDate(r.created_at)} · <strong>{r.symbol}</strong> · <span className="text-primary">{r.step}</span>
                    </span>
                  </div>
                  <p className="reasoning-message mb-1">{r.message}</p>
                  {r.data && Object.keys(r.data).length > 0 && (
                    <pre className="reasoning-data">{JSON.stringify(r.data, null, 2)}</pre>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="agent-history-card card shadow-sm border-0">
        <div className="card-body">
          <h5 className="card-title d-flex align-items-center gap-2">
            <FaHistory /> History
          </h5>
          <div className="table-responsive">
            <table className="table table-sm table-hover">
              <thead className="table-light">
                <tr>
                  <th>Time</th>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th className="text-end">Position size</th>
                  <th>Reason</th>
                  <th>Executed</th>
                  <th>Guardrail</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr><td colSpan={7} className="text-muted text-center py-4">No history yet.</td></tr>
                ) : (
                  history.map((h) => (
                    <tr key={h.id}>
                      <td className="small">{formatDate(h.created_at)}</td>
                      <td><strong>{h.symbol}</strong></td>
                      <td>
                        <span className={`badge ${h.action === "Buy" ? "bg-success" : h.action === "Sell" ? "bg-danger" : "bg-secondary"}`}>
                          {h.action}
                        </span>
                      </td>
                      <td className="text-end">{(h.position_size * 100).toFixed(1)}%</td>
                      <td className="small text-break" style={{ maxWidth: 280 }}>{h.reason}</td>
                      <td>{h.executed ? "Yes" : "—"}</td>
                      <td>{h.guardrail_triggered ? "Yes" : "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
