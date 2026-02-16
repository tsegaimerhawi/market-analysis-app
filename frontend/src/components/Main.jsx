import React, { useState, useEffect } from "react";
import SideBar from "./SideBar";
import Watchlist from "./Watchlist";
import StockAnalysis from "./StockAnalysis";
import ScrapeArticles from "./ScrapeArticles";
import FuturePrediction from "./FuturePrediction";
import Portfolio from "./Portfolio";
import Trade from "./Trade";
import TradingAgent from "./TradingAgent";
import VolatileSymbols from "./VolatileSymbols";
import NormalSymbols from "./NormalSymbols";

const VIEW_STORAGE_KEY = "marketAppActiveView";
const VALID_VIEWS = ["watchlist", "analysis", "scrape", "future_prediction", "portfolio", "trade", "agent", "normal_symbols", "volatile_symbols"];

function getStoredView() {
  try {
    const s = sessionStorage.getItem(VIEW_STORAGE_KEY);
    if (s && VALID_VIEWS.includes(s)) return s;
  } catch (e) {}
  return "watchlist";
}

export default function Main() {
  const [activeView, setActiveView] = useState(getStoredView);
  const [tradeSymbol, setTradeSymbol] = useState("");

  useEffect(() => {
    try {
      sessionStorage.setItem(VIEW_STORAGE_KEY, activeView);
    } catch (e) {}
  }, [activeView]);

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
          {activeView === "normal_symbols" && <NormalSymbols />}
          {activeView === "volatile_symbols" && <VolatileSymbols />}
        </div>
      </div>
    </div>
  );
}
