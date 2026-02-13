import React, { useState } from "react";
import { FaBook } from "react-icons/fa";
import AlgorithmTutorials from "./AlgorithmTutorials";

export default function SideBar({ activeView, setActiveView }) {
  const [showTutorials, setShowTutorials] = useState(false);

  return (
    <>
      <div
        className="bg-light border-end flex-shrink-0"
        style={{ minHeight: "100vh", width: "220px" }}
      >
        <div className="p-3">
          <h5 className="text-secondary mb-0">Market Analysis</h5>
          <hr />
          <nav className="nav flex-column gap-1">
            <button
              type="button"
              className={`nav-link text-start border-0 bg-transparent rounded px-3 py-2 ${activeView === "watchlist" ? "active fw-bold" : "text-dark"}`}
              onClick={() => setActiveView("watchlist")}
            >
              Watchlist
            </button>
            <button
              type="button"
              className={`nav-link text-start border-0 bg-transparent rounded px-3 py-2 ${activeView === "analysis" ? "active fw-bold" : "text-dark"}`}
              onClick={() => setActiveView("analysis")}
            >
              Stock Analysis
            </button>
            <button
              type="button"
              className={`nav-link text-start border-0 bg-transparent rounded px-3 py-2 ${activeView === "scrape" ? "active fw-bold" : "text-dark"}`}
              onClick={() => setActiveView("scrape")}
            >
              Scrape Articles
            </button>
            <button
              type="button"
              className={`nav-link text-start border-0 bg-transparent rounded px-3 py-2 ${activeView === "future_prediction" ? "active fw-bold" : "text-dark"}`}
              onClick={() => setActiveView("future_prediction")}
            >
              Future Prediction
            </button>
            <button
              type="button"
              className={`nav-link text-start border-0 bg-transparent rounded px-3 py-2 ${activeView === "portfolio" ? "active fw-bold" : "text-dark"}`}
              onClick={() => setActiveView("portfolio")}
            >
              Portfolio
            </button>
            <button
              type="button"
              className={`nav-link text-start border-0 bg-transparent rounded px-3 py-2 ${activeView === "trade" ? "active fw-bold" : "text-dark"}`}
              onClick={() => setActiveView("trade")}
            >
              Trade
            </button>
            <button
              type="button"
              className={`nav-link text-start border-0 bg-transparent rounded px-3 py-2 ${activeView === "agent" ? "active fw-bold" : "text-dark"}`}
              onClick={() => setActiveView("agent")}
            >
              Trading Agent
            </button>
          </nav>

          <hr />
          <h6 className="text-secondary mb-3">Resources</h6>
          <button
            type="button"
            className="btn btn-outline-primary w-100 d-flex align-items-center justify-content-center gap-2"
            onClick={() => setShowTutorials(true)}
          >
            <FaBook />
            Algorithm Tutorials
          </button>
        </div>
      </div>

      <AlgorithmTutorials isOpen={showTutorials} onClose={() => setShowTutorials(false)} />
    </>
  );
}
