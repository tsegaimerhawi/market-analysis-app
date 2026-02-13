import React, { useState } from "react";
import SideBar from "./SideBar";
import Watchlist from "./Watchlist";
import StockAnalysis from "./StockAnalysis";
import ScrapeArticles from "./ScrapeArticles";
import FuturePrediction from "./FuturePrediction";
import Portfolio from "./Portfolio";
import Trade from "./Trade";
import TradingAgent from "./TradingAgent";

export default function Main() {
  const [activeView, setActiveView] = useState("watchlist");
  const [tradeSymbol, setTradeSymbol] = useState("");

  return (
    <div className="d-flex flex-grow-1 min-vh-100">
      <SideBar activeView={activeView} setActiveView={setActiveView} />
      <div className="flex-grow-1 overflow-auto">
        <div className="container py-4">
          {activeView === "watchlist" && <Watchlist onTradeSymbol={(sym) => { setTradeSymbol(sym || ""); setActiveView("trade"); }} />}
          {activeView === "analysis" && <StockAnalysis />}
          {activeView === "scrape" && <ScrapeArticles />}
          {activeView === "future_prediction" && <FuturePrediction />}
          {activeView === "portfolio" && <Portfolio />}
          {activeView === "trade" && <Trade initialSymbol={tradeSymbol} onConsumeSymbol={() => setTradeSymbol("")} />}
          {activeView === "agent" && <TradingAgent />}
        </div>
      </div>
    </div>
  );
}
