import React from "react";

export default function SideBar({ activeView, setActiveView }) {
  return (
    <div
      className="bg-light border-end"
      style={{ minHeight: "100vh", width: "200px" }}
    >
      <div className="p-3">
        <h5 className="text-secondary mb-0">Market Analysis</h5>
        <hr />
        <nav className="nav flex-column">
          <button
            type="button"
            className={`nav-link text-start border-0 bg-transparent ${activeView === "watchlist" ? "active fw-bold" : "text-dark"}`}
            onClick={() => setActiveView("watchlist")}
          >
            Watchlist
          </button>
          <button
            type="button"
            className={`nav-link text-start border-0 bg-transparent ${activeView === "analysis" ? "active fw-bold" : "text-dark"}`}
            onClick={() => setActiveView("analysis")}
          >
            Stock Analysis
          </button>
          <button
            type="button"
            className={`nav-link text-start border-0 bg-transparent ${activeView === "scrape" ? "active fw-bold" : "text-dark"}`}
            onClick={() => setActiveView("scrape")}
          >
            Scrape Articles
          </button>
          <button
            type="button"
            className={`nav-link text-start border-0 bg-transparent ${activeView === "future_prediction" ? "active fw-bold" : "text-dark"}`}
            onClick={() => setActiveView("future_prediction")}
          >
            Future Prediction
          </button>
        </nav>
      </div>
    </div>
  );
}
