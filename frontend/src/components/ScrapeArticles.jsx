import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://localhost:5001";

export default function ScrapeArticles() {
  const [newspapers, setNewspapers] = useState([]);
  const [selectedNewspaper, setSelectedNewspaper] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [articles, setArticles] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${API_BASE}/api/newspapers`).then((res) => {
      setNewspapers(res.data.newspapers || []);
      if (res.data.newspapers?.length && !selectedNewspaper) {
        setSelectedNewspaper(res.data.newspapers[0].id);
      }
    }).catch(() => setNewspapers([]));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedNewspaper) {
      setError("Select a newspaper.");
      return;
    }
    setError(null);
    setLoading(true);
    setArticles([]);
    try {
      const res = await axios.post(`${API_BASE}/api/scrape-articles`, {
        newspaper: selectedNewspaper,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      });
      setArticles(res.data.articles || []);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Failed to fetch articles.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="scrape-articles">
      <h1 className="mb-4">Scrape Articles</h1>
      <p className="text-muted mb-4">Choose a news source and date range to fetch recent articles for market research.</p>

      <form onSubmit={handleSubmit} className="card card-body mb-4">
        <h2 className="h5 mb-3">Search criteria</h2>
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label">Newspaper:</label>
            <select
              className="form-select"
              value={selectedNewspaper}
              onChange={(e) => setSelectedNewspaper(e.target.value)}
              aria-label="Select newspaper"
            >
              <option value="">Select a newspaper…</option>
              {newspapers.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label">Start Date:</label>
            <input
              type="date"
              className="form-control"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label">End Date:</label>
            <input
              type="date"
              className="form-control"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
        <div className="mt-3">
          <button type="submit" className="btn btn-primary" disabled={loading || !selectedNewspaper}>
            {loading ? "Fetching…" : "Fetch articles"}
          </button>
        </div>
      </form>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {articles.length > 0 && (
        <>
          <h2 className="h5 mb-3">Articles ({articles.length})</h2>
          <ul className="list-group">
            {articles.map((a, i) => (
              <li key={i} className="list-group-item">
                <div className="fw-medium">
                  {a.link ? (
                    <a href={a.link} target="_blank" rel="noopener noreferrer">
                      {a.title || "Untitled"}
                    </a>
                  ) : (
                    a.title || "Untitled"
                  )}
                </div>
                {a.published && (
                  <small className="text-muted">{new Date(a.published).toLocaleString()}</small>
                )}
                {a.summary && <p className="small text-muted mb-0 mt-1">{a.summary}</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
