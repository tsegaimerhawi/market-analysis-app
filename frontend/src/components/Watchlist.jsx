import React, { useState, useEffect } from "react";
import axios from "axios";
import CompanyInfo from "./CompanyInfo";

const API_BASE = "http://localhost:5000";

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [infoSymbol, setInfoSymbol] = useState(null);

  const loadWatchlist = () => {
    axios.get(`${API_BASE}/api/watchlist`).then((res) => {
      setWatchlist(res.data.watchlist || []);
    }).catch(() => setWatchlist([]));
  };

  const loadCompanies = () => {
    axios.get(`${API_BASE}/api/companies`).then((res) => {
      setCompanies(res.data.companies || []);
    }).catch(() => setCompanies([]));
  };

  useEffect(() => {
    loadWatchlist();
    loadCompanies();
  }, []);

  const watchlistSymbols = new Set(watchlist.map((w) => w.symbol));
  const addableCompanies = companies.filter((c) => !watchlistSymbols.has(c.symbol));

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!selectedCompany) {
      setError("Select a company from the list.");
      return;
    }
    const company = companies.find((c) => `${c.symbol}|${c.name}` === selectedCompany);
    if (!company || watchlistSymbols.has(company.symbol)) {
      setError("Company already in watchlist or invalid selection.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/api/watchlist`, {
        symbol: company.symbol,
        company_name: company.name,
      });
      setSelectedCompany("");
      loadWatchlist();
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Failed to add");
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (idOrSymbol) => {
    try {
      await axios.delete(`${API_BASE}/api/watchlist/${encodeURIComponent(idOrSymbol)}`);
      loadWatchlist();
      if (infoSymbol === idOrSymbol || String(infoSymbol) === String(idOrSymbol)) setInfoSymbol(null);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Failed to remove");
    }
  };

  return (
    <div className="watchlist">
      <h1 className="mb-4">Watchlist</h1>
      <p className="text-muted mb-4">Choose a company from the list below and add it to your watchlist. Use them in Stock Analysis and view full company info.</p>

      <form onSubmit={handleAdd} className="card card-body mb-4">
        <label className="form-label">Add company to watchlist</label>
        <div className="row g-2 align-items-end">
          <div className="col-md-8">
            <select
              className="form-select"
              value={selectedCompany}
              onChange={(e) => setSelectedCompany(e.target.value)}
              aria-label="Select company"
            >
              <option value="">Select a company (symbol – name)…</option>
              {addableCompanies.map((c) => (
                <option key={c.symbol} value={`${c.symbol}|${c.name}`}>
                  {c.symbol} – {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <button type="submit" className="btn btn-primary w-100" disabled={loading || !selectedCompany || addableCompanies.length === 0}>
              {loading ? "Adding…" : "Add to watchlist"}
            </button>
          </div>
        </div>
        {addableCompanies.length === 0 && companies.length > 0 && (
          <p className="text-muted small mb-0 mt-2">All listed companies are already in your watchlist.</p>
        )}
      </form>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      <h2 className="h5 mb-3">Saved companies</h2>
      {watchlist.length === 0 ? (
        <p className="text-muted">No companies in your watchlist. Select one from the dropdown above and click Add to watchlist.</p>
      ) : (
        <ul className="list-group mb-4">
          {watchlist.map((item) => (
            <li key={item.id} className="list-group-item d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-2">
              <span className="flex-grow-1">
                <strong>{item.symbol}</strong>
                {item.company_name && item.company_name !== item.symbol && (
                  <span className="text-muted ms-2">{item.company_name}</span>
                )}
              </span>
              <span className="d-flex flex-wrap gap-1">
                <button
                  type="button"
                  className="btn btn-sm btn-outline-primary me-1"
                  onClick={() => setInfoSymbol(infoSymbol === item.symbol ? null : item.symbol)}
                >
                  {infoSymbol === item.symbol ? "Hide info" : "Company info"}
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-danger"
                  onClick={() => handleRemove(item.symbol)}
                >
                  Remove
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      {infoSymbol && <CompanyInfo symbol={infoSymbol} onClose={() => setInfoSymbol(null)} />}
    </div>
  );
}
