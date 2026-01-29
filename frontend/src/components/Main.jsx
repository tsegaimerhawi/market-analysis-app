import React, { useState } from "react";
import SideBar from "./SideBar";
import Watchlist from "./Watchlist";
import StockAnalysis from "./StockAnalysis";
import ScrapeArticles from "./ScrapeArticles";

export default function Main() {
  const [activeView, setActiveView] = useState("watchlist");

  return (
    <div className="d-flex flex-grow-1 min-vh-100">
      <SideBar activeView={activeView} setActiveView={setActiveView} />
      <div className="flex-grow-1 overflow-auto">
        <div className="container py-4">
          {activeView === "watchlist" && <Watchlist />}
          {activeView === "analysis" && <StockAnalysis />}
          {activeView === "scrape" && <ScrapeArticles />}
        </div>
      </div>
    </div>
  );
}
