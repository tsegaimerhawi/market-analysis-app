import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://localhost:5000";

const FRIENDLY_KEYS = {
  symbol: "Symbol",
  shortName: "Short name",
  longName: "Long name",
  sector: "Sector",
  industry: "Industry",
  sectorDisp: "Sector (display)",
  industryDisp: "Industry (display)",
  exchange: "Exchange",
  quoteType: "Quote type",
  market: "Market",
  marketCap: "Market cap",
  enterpriseValue: "Enterprise value",
  trailingPE: "Trailing P/E",
  forwardPE: "Forward P/E",
  beta: "Beta",
  dividendYield: "Dividend yield",
  dividendRate: "Dividend rate",
  exDividendDate: "Ex-dividend date",
  payoutRatio: "Payout ratio",
  fiftyTwoWeekHigh: "52w high",
  fiftyTwoWeekLow: "52w low",
  fiftyDayAverage: "50d average",
  twoHundredDayAverage: "200d average",
  volume: "Volume",
  averageVolume: "Average volume",
  open: "Open",
  previousClose: "Previous close",
  regularMarketPrice: "Regular market price",
  regularMarketOpen: "Regular market open",
  regularMarketDayHigh: "Day high",
  regularMarketDayLow: "Day low",
  regularMarketVolume: "Regular market volume",
  address1: "Address",
  city: "City",
  state: "State",
  country: "Country",
  website: "Website",
  fullTimeEmployees: "Full-time employees",
  longBusinessSummary: "Business summary",
};

export default function CompanyInfo({ symbol, onClose }) {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    axios.get(`${API_BASE}/api/company/${encodeURIComponent(symbol)}`).then((res) => {
      setInfo(res.data);
      setLoading(false);
    }).catch((err) => {
      setError(err.response?.data?.error || err.message);
      setLoading(false);
    });
  }, [symbol]);

  if (!symbol) return null;

  return (
    <div className="card card-body mb-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3 className="h5 mb-0">Company info: {symbol}</h3>
        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={onClose}>
          Close
        </button>
      </div>
      {loading && <p className="text-muted">Loading…</p>}
      {error && <div className="alert alert-danger">{error}</div>}
      {info && !info.error && (
        <div className="company-info">
          {info.longBusinessSummary && (
            <div className="mb-3">
              <strong>Business summary</strong>
              <p className="text-muted small mb-0">{info.longBusinessSummary}</p>
            </div>
          )}
          <div className="row g-2">
            {Object.entries(info)
              .filter(([k, v]) => v != null && v !== "" && k !== "longBusinessSummary" && k !== "error")
              .map(([key, value]) => {
                let display = value;
                if (typeof value === "number") display = Number.isInteger(value) ? value : value.toFixed(4);
                else if (Array.isArray(value)) display = value.slice(0, 10).join(", ") + (value.length > 10 ? "…" : "");
                else if (typeof value === "object") display = JSON.stringify(value).slice(0, 80) + (JSON.stringify(value).length > 80 ? "…" : "");
                else display = String(value);
                return (
                  <div key={key} className="col-md-6 col-lg-4">
                    <small className="text-muted">{FRIENDLY_KEYS[key] || key}</small>
                    <div className="fw-medium small">{display}</div>
                  </div>
                );
              })}
          </div>
          <details className="mt-3">
            <summary className="text-muted small">Raw JSON (everything from system)</summary>
            <pre className="small bg-light p-2 rounded mt-1 overflow-auto" style={{ maxHeight: 300 }}>
              {JSON.stringify(info, null, 2)}
            </pre>
          </details>
        </div>
      )}
      {info && info.error && <div className="alert alert-warning">{info.error}</div>}
    </div>
  );
}
