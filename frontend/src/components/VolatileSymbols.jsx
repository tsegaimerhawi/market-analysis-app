import React, { useState, useEffect } from "react";
import axios from "axios";
import { FaSync, FaPlus, FaTrash, FaSave, FaChartLine } from "react-icons/fa";
import "./VolatileSymbols.css";

const API_BASE = "http://localhost:5001";

export default function VolatileSymbols() {
  const [symbols, setSymbols] = useState([]);
  const [newSymbol, setNewSymbol] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    axios
      .get(`${API_BASE}/api/volatile-candidates`)
      .then((res) => setSymbols(res.data.symbols || []))
      .catch((err) => setError(err.response?.data?.error || err.message || "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleAdd = () => {
    const sym = (newSymbol || "").trim().toUpperCase();
    if (!sym) return;
    if (symbols.includes(sym)) {
      setMessage(`${sym} is already in the list`);
      return;
    }
    setSymbols([...symbols, sym]);
    setNewSymbol("");
    setMessage(null);
  };

  const handleRemove = (sym) => {
    setSymbols(symbols.filter((s) => s !== sym));
    setMessage(null);
  };

  const handleSave = () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    axios
      .put(`${API_BASE}/api/volatile-candidates`, { symbols })
      .then((res) => {
        setSymbols(res.data.symbols || []);
        setMessage("Saved. The agent will use this list when Volatile stocks is on.");
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Failed to save"))
      .finally(() => setSaving(false));
  };

  const handleRefreshFromUniverse = () => {
    setRefreshing(true);
    setError(null);
    setMessage(null);
    axios
      .post(`${API_BASE}/api/volatile-candidates/refresh-from-universe?top_n=40`)
      .then((res) => {
        setSymbols(res.data.symbols || []);
        setMessage(res.data.message || "List updated from market (top volatile from universe).");
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Refresh failed"))
      .finally(() => setRefreshing(false));
  };

  return (
    <div className="volatile-symbols-page">
      <header className="volatile-page-header">
        <h1><FaChartLine className="me-2" />Volatile Symbols</h1>
        <p className="subtitle text-muted">
          Candidate list for the 8h volatility scanner. When &quot;Volatile stocks&quot; is on in the Trading Agent, it trades from this list (top 25 by volatility). Edit below or refresh from the larger universe.
        </p>
      </header>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="alert alert-success" role="alert">
          {message}
        </div>
      )}

      <section className="card shadow-sm border-0 mb-4">
        <div className="card-body">
          <h5 className="card-title mb-3">Candidate list (volatile_symbols.json)</h5>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <input
              type="text"
              className="form-control form-control-sm text-uppercase"
              style={{ width: 120 }}
              placeholder="e.g. GME"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={handleAdd}>
              <FaPlus className="me-1" /> Add
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleSave}
              disabled={saving}
            >
              <FaSave className="me-1" /> {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              className="btn btn-warning btn-sm"
              onClick={handleRefreshFromUniverse}
              disabled={refreshing}
              title="Scan data/volatile_universe.json and replace list with top 40 by 8h volatility"
            >
              <FaSync className="me-1" /> {refreshing ? "Scanning…" : "Refresh from market"}
            </button>
          </div>
          {loading ? (
            <p className="text-muted mb-0">Loading…</p>
          ) : (
            <div className="volatile-symbols-list">
              {symbols.length === 0 ? (
                <p className="text-muted mb-0">No symbols. Add some or use &quot;Refresh from market&quot;.</p>
              ) : (
                <ul className="list-inline mb-0">
                  {symbols.map((sym) => (
                    <li key={sym} className="list-inline-item volatile-symbol-tag">
                      <span>{sym}</span>
                      <button
                        type="button"
                        className="btn btn-link btn-sm p-0 ms-1 text-danger"
                        onClick={() => handleRemove(sym)}
                        title={`Remove ${sym}`}
                        aria-label={`Remove ${sym}`}
                      >
                        <FaTrash />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </section>

      <section className="card shadow-sm border-0">
        <div className="card-body">
          <h6 className="text-muted">How it works</h6>
          <ul className="small text-muted mb-0">
            <li><strong>Candidate list</strong> — Symbols above are stored in <code>backend/data/volatile_symbols.json</code>.</li>
            <li><strong>Refresh from market</strong> — Scans <code>volatile_universe.json</code> (larger set), ranks by 8h volatility + small-cap bias, and replaces the candidate list with the top 40.</li>
            <li>When the Trading Agent has &quot;Volatile stocks&quot; on, it uses this list and trades the top 25 most volatile from it each cycle.</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
