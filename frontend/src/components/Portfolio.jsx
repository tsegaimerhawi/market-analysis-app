import React, { useState, useEffect } from "react";
import axios from "axios";
import { FaWallet, FaChartLine, FaHistory, FaRedo } from "react-icons/fa";

const API_BASE = "http://localhost:5000";

function formatMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(n);
}

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState({ cash_balance: 0, positions: [], orders: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [prices, setPrices] = useState({});
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [cashAmount, setCashAmount] = useState("");
  const [cashLoading, setCashLoading] = useState(false);
  const [cashMessage, setCashMessage] = useState(null);

  const loadPortfolio = () => {
    setLoading(true);
    axios
      .get(`${API_BASE}/api/portfolio`)
      .then((res) => {
        setPortfolio(res.data);
        setError(null);
        // Optionally fetch current prices for positions to show market value
        const symbols = (res.data.positions || []).map((p) => p.symbol);
        if (symbols.length > 0) {
          Promise.all(symbols.map((s) => axios.get(`${API_BASE}/api/quote/${s}`)))
            .then((quotes) => {
              const map = {};
              quotes.forEach((q, i) => {
                if (q.data && q.data.symbol) map[q.data.symbol] = q.data.price;
              });
              setPrices(map);
            })
            .catch(() => {});
        } else {
          setPrices({});
        }
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Failed to load portfolio"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadPortfolio();
  }, []);

  const handleCashAction = (action) => {
    const amt = parseFloat(cashAmount);
    if (!Number.isFinite(amt) || amt <= 0) {
      setCashMessage("Enter a positive amount.");
      return;
    }
    setCashLoading(true);
    setCashMessage(null);
    axios
      .post(`${API_BASE}/api/portfolio/cash`, { amount: amt, action })
      .then((res) => {
        setCashMessage(res.data.message);
        setCashAmount("");
        loadPortfolio();
      })
      .catch((err) => setCashMessage(err.response?.data?.error || "Failed"))
      .finally(() => setCashLoading(false));
  };

  const handleReset = () => {
    setResetting(true);
    setError(null);
    axios
      .post(`${API_BASE}/api/portfolio/reset`)
      .then((res) => {
        setPortfolio({ ...portfolio, cash_balance: res.data.cash_balance, positions: [], orders: [] });
        setPrices({});
        setShowResetConfirm(false);
        loadPortfolio();
      })
      .catch((err) => setError(err.response?.data?.error || err.message || "Reset failed"))
      .finally(() => setResetting(false));
  };

  if (loading && portfolio.positions?.length === 0) {
    return (
      <div className="portfolio">
        <h1 className="mb-4">Portfolio</h1>
        <p className="text-muted">Loading…</p>
      </div>
    );
  }

  const { cash_balance, positions = [], orders = [] } = portfolio;
  const positionsValue = positions.reduce((sum, p) => {
    const qty = parseFloat(p.quantity);
    const mkt = prices[p.symbol];
    const cost = parseFloat(p.avg_cost);
    return sum + qty * (mkt != null ? mkt : cost);
  }, 0);
  const totalValue = cash_balance + positionsValue;

  return (
    <div className="portfolio">
      <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-4">
        <div>
          <h1 className="mb-2">Portfolio</h1>
          <p className="text-muted mb-0">Paper trading: view your cash, positions, and order history. Use <strong>Trade</strong> to buy or sell.</p>
        </div>
        <button
          type="button"
          className="btn btn-outline-danger d-flex align-items-center gap-2"
          onClick={() => setShowResetConfirm(true)}
        >
          <FaRedo /> Reset paper account
        </button>
      </div>

      {showResetConfirm && (
        <div className="modal show d-block" style={{ backgroundColor: "rgba(0,0,0,0.5)" }} tabIndex={-1}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Reset paper account</h5>
                <button type="button" className="btn-close" onClick={() => setShowResetConfirm(false)} aria-label="Close" />
              </div>
              <div className="modal-body">
                This will reset cash to $100,000 and clear all positions and orders. This cannot be undone. Continue?
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowResetConfirm(false)} disabled={resetting}>Cancel</button>
                <button type="button" className="btn btn-danger" onClick={handleReset} disabled={resetting}>
                  {resetting ? "Resetting…" : "Reset"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {cashMessage && (
        <div className="alert alert-success py-2" role="alert">
          {cashMessage}
        </div>
      )}

      <div className="card shadow-sm border-0 mb-4">
        <div className="card-body">
          <h5 className="card-title mb-3">Deposit / Withdraw (paper)</h5>
          <div className="row g-2 align-items-end">
            <div className="col-auto">
              <label className="form-label small text-muted mb-0">Amount ($)</label>
              <input
                type="number"
                className="form-control"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={cashAmount}
                onChange={(e) => setCashAmount(e.target.value)}
                disabled={cashLoading}
              />
            </div>
            <div className="col-auto">
              <button type="button" className="btn btn-success" onClick={() => handleCashAction("deposit")} disabled={cashLoading || !cashAmount}>Deposit</button>
            </div>
            <div className="col-auto">
              <button type="button" className="btn btn-outline-secondary" onClick={() => handleCashAction("withdraw")} disabled={cashLoading || !cashAmount}>Withdraw</button>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="card shadow-sm border-0 h-100">
            <div className="card-body d-flex align-items-center">
              <FaWallet className="text-primary me-3" style={{ fontSize: "2rem" }} />
              <div>
                <div className="text-muted small text-uppercase">Cash balance</div>
                <div className="fw-bold fs-4">{formatMoney(cash_balance)}</div>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card shadow-sm border-0 h-100">
            <div className="card-body d-flex align-items-center">
              <FaChartLine className="text-success me-3" style={{ fontSize: "2rem" }} />
              <div>
                <div className="text-muted small text-uppercase">Positions value</div>
                <div className="fw-bold fs-4">{formatMoney(positionsValue)}</div>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card shadow-sm border-0 h-100">
            <div className="card-body d-flex align-items-center">
              <FaWallet className="text-secondary me-3" style={{ fontSize: "2rem" }} />
              <div>
                <div className="text-muted small text-uppercase">Total value</div>
                <div className="fw-bold fs-4">{formatMoney(totalValue)}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <h2 className="h5 mb-3">Positions</h2>
      {positions.length === 0 ? (
        <p className="text-muted mb-4">No positions yet. Go to <strong>Trade</strong> to buy stocks.</p>
      ) : (
        <div className="table-responsive mb-4">
          <table className="table table-hover align-middle">
            <thead className="table-light">
              <tr>
                <th>Symbol</th>
                <th className="text-end">Quantity</th>
                <th className="text-end">Avg cost</th>
                <th className="text-end">Market price</th>
                <th className="text-end">Market value</th>
                <th className="text-end">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => {
                const qty = parseFloat(p.quantity);
                const avgCost = parseFloat(p.avg_cost);
                const mkt = prices[p.symbol];
                const costBasis = qty * avgCost;
                const mktValue = mkt != null ? qty * mkt : costBasis;
                const pl = mkt != null ? mktValue - costBasis : null;
                return (
                  <tr key={p.id}>
                    <td><strong>{p.symbol}</strong></td>
                    <td className="text-end">{qty}</td>
                    <td className="text-end">{formatMoney(avgCost)}</td>
                    <td className="text-end">{mkt != null ? formatMoney(mkt) : "—"}</td>
                    <td className="text-end">{formatMoney(mktValue)}</td>
                    <td className={`text-end ${pl != null ? (pl >= 0 ? "text-success" : "text-danger") : ""}`}>
                      {pl != null ? `${pl >= 0 ? "+" : ""}${formatMoney(pl)}` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="h5 mb-3"><FaHistory className="me-2" />Recent orders</h2>
      {orders.length === 0 ? (
        <p className="text-muted">No orders yet.</p>
      ) : (
        <div className="table-responsive">
          <table className="table table-sm table-hover">
            <thead className="table-light">
              <tr>
                <th>Date</th>
                <th>Side</th>
                <th>Symbol</th>
                <th className="text-end">Qty</th>
                <th className="text-end">Price</th>
                <th className="text-end">Total</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.created_at?.slice(0, 19).replace("T", " ")}</td>
                  <td><span className={`badge ${o.side === "buy" ? "bg-success" : "bg-danger"}`}>{o.side}</span></td>
                  <td><strong>{o.symbol}</strong></td>
                  <td className="text-end">{parseFloat(o.quantity)}</td>
                  <td className="text-end">{formatMoney(parseFloat(o.price))}</td>
                  <td className="text-end">{formatMoney(parseFloat(o.total))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
