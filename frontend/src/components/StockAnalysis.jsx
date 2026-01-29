import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_BASE = "http://localhost:5000";

export default function StockAnalysis() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [watchlist, setWatchlist] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [algorithms, setAlgorithms] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [chartAlgorithm, setChartAlgorithm] = useState("");

  useEffect(() => {
    axios.get(`${API_BASE}/api/algorithms`).then((res) => {
      const list = res.data.algorithms || [];
      setAlgorithms(list);
      setSelectedIds(new Set(list.map((a) => a.id)));
      if (list.length) setChartAlgorithm(list[0].name);
    }).catch(() => setAlgorithms([]));
  }, []);

  useEffect(() => {
    axios.get(`${API_BASE}/api/watchlist`).then((res) => {
      const list = res.data.watchlist || [];
      setWatchlist(list);
      if (list.length && !selectedSymbol) setSelectedSymbol(list[0].symbol);
    }).catch(() => setWatchlist([]));
  }, []);

  const toggleAlgorithm = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedSymbol) {
      setError("Select a company from your watchlist (or add one in Watchlist).");
      return;
    }
    setError(null);
    setLoading(true);
    setResults([]);
    const formData = new FormData();
    formData.append("symbol", selectedSymbol);
    formData.append("startDate", startDate);
    formData.append("endDate", endDate);
    formData.append("algorithms", JSON.stringify([...selectedIds]));

    try {
      const res = await axios.post(`${API_BASE}/api/compare`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResults(res.data.results || []);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  const chartResult = results.find((r) => r.name === chartAlgorithm) || results.find((r) => r.dates?.length);
  const hasChart = chartResult?.dates?.length && chartResult?.actual?.length && chartResult?.predictions?.length;

  return (
    <div className="stock-analysis">
      <h1 className="mb-4">Stock Analysis</h1>
      <p className="text-muted mb-4">Choose a company from your watchlist, set the date range, select algorithms, and compare results.</p>

      <form onSubmit={handleSubmit} className="analysis-form card card-body mb-4">
        <div className="row g-3">
          <div className="col-md-3">
            <label className="form-label">Company</label>
            <select
              className="form-select"
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
            >
              <option value="">Select company…</option>
              {watchlist.map((item) => (
                <option key={item.id} value={item.symbol}>
                  {item.symbol} {item.company_name && item.company_name !== item.symbol ? `(${item.company_name})` : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label">Start Date</label>
            <input
              type="date"
              className="form-control"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label">End Date</label>
            <input
              type="date"
              className="form-control"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <div className="col-md-2 d-flex align-items-end">
            <button type="submit" className="btn btn-primary w-100" disabled={loading || watchlist.length === 0}>
              {loading ? "Running…" : "Compare algorithms"}
            </button>
          </div>
        </div>

        <div className="mt-3">
          <label className="form-label">Algorithms to compare</label>
          <div className="d-flex flex-wrap gap-3">
            {algorithms.map((a) => (
              <label key={a.id} className="form-check form-check-inline">
                <input
                  type="checkbox"
                  className="form-check-input"
                  checked={selectedIds.has(a.id)}
                  onChange={() => toggleAlgorithm(a.id)}
                />
                <span className="form-check-label">{a.name}</span>
              </label>
            ))}
          </div>
        </div>
      </form>

      {watchlist.length === 0 && (
        <div className="alert alert-info">
          Add companies in <strong>Watchlist</strong> first, then run analysis here.
        </div>
      )}

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <>
          <h2 className="h5 mb-3">Results</h2>
          <div className="table-responsive mb-4">
            <table className="table table-bordered table-hover">
              <thead className="table-light">
                <tr>
                  <th>Algorithm</th>
                  <th>MAE</th>
                  <th>RMSE</th>
                  <th>MAPE (%)</th>
                  <th>Direction accuracy (%)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i}>
                    <td>{r.name}</td>
                    <td>{r.metrics?.mae != null ? r.metrics.mae : "—"}</td>
                    <td>{r.metrics?.rmse != null ? r.metrics.rmse : "—"}</td>
                    <td>{r.metrics?.mape != null ? r.metrics.mape : "—"}</td>
                    <td>{r.metrics?.direction_accuracy != null ? r.metrics.direction_accuracy : "—"}</td>
                    <td>{r.error ? <span className="text-danger">{r.error}</span> : "OK"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {hasChart && (
            <div className="card card-body">
              <label className="form-label">Chart: Actual vs predicted</label>
              <select
                className="form-select mb-2 w-auto"
                value={chartAlgorithm}
                onChange={(e) => setChartAlgorithm(e.target.value)}
              >
                {results.filter((r) => r.dates?.length).map((r, i) => (
                  <option key={i} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
              <ChartResult result={chartResult || results.find((r) => r.dates?.length)} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ChartResult({ result }) {
  if (!result?.dates?.length || !result.actual?.length || !result.predictions?.length) return null;
  const len = Math.min(result.dates.length, result.actual.length, result.predictions.length);
  const data = result.dates.slice(0, len).map((d, i) => ({
    date: String(d).slice(0, 10),
    actual: result.actual[i],
    predicted: result.predictions[i],
  }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="actual" stroke="#0d6efd" name="Actual" dot={false} />
        <Line type="monotone" dataKey="predicted" stroke="#dc3545" name="Predicted" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
