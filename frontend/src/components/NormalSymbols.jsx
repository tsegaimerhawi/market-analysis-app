import React, { useState, useEffect } from "react";
import axios from "axios";
import { FaPlus, FaTrash, FaSave, FaBriefcase } from "react-icons/fa";
import "./VolatileSymbols.css";

const API_BASE = "http://localhost:5001";

export default function NormalSymbols() {
  const [symbols, setSymbols] = useState([]);
  const [newSymbol, setNewSymbol] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    axios
      .get(`${API_BASE}/api/normal-candidates`)
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
      .put(`${API_BASE}/api/normal-candidates`, { symbols })
      .then((res) => {
        setSymbols(res.data.symbols || []);
        setMessage("Saved. The agent always trades from this list (normal stocks) plus your watchlist.");
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Failed to save"))
      .finally(() => setSaving(false));
  };

  return (
    <div className="volatile-symbols-page">
      <header className="volatile-page-header">
        <h1><FaBriefcase className="me-2" />Normal Symbols</h1>
        <p className="subtitle text-muted">
          Stable / blue-chip stocks (e.g. Amazon, NVIDIA, Google, Apple, Meta). The Trading Agent always includes this list when it runs, plus your watchlist and—when on—the volatile list.
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
          <h5 className="card-title mb-3">Normal stocks list (normal_symbols.json)</h5>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <input
              type="text"
              className="form-control form-control-sm text-uppercase"
              style={{ width: 120 }}
              placeholder="e.g. AAPL"
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
          </div>
          {loading ? (
            <p className="text-muted mb-0">Loading…</p>
          ) : (
            <div className="volatile-symbols-list">
              {symbols.length === 0 ? (
                <p className="text-muted mb-0">No symbols. Add normal/stable stocks (e.g. AAPL, NVDA, AMZN, META).</p>
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
          <h6 className="text-muted">Two lists</h6>
          <ul className="small text-muted mb-0">
            <li><strong>Normal symbols</strong> — Blue-chip / stable names (this page). Stored in <code>backend/data/normal_symbols.json</code>. The agent always runs on these plus your watchlist.</li>
            <li><strong>Volatile symbols</strong> — High-volatility candidates (see Volatile Symbols). When &quot;Volatile stocks&quot; is on, the agent also trades the top 25 from that list.</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
