import React, { useState, useEffect } from "react";
import axios from "axios";
import { FaArrowUp, FaArrowDown, FaChartLine, FaTimes } from "react-icons/fa";
import "./Trade.css";

const API_BASE = "http://localhost:5001";

function formatMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

export default function Trade({ initialSymbol = "", onConsumeSymbol }) {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [side, setSide] = useState("buy");
  const [quantity, setQuantity] = useState("");
  const [quote, setQuote] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [orderType, setOrderType] = useState("market");
  const [limitPrice, setLimitPrice] = useState("");
  const [limitOrders, setLimitOrders] = useState([]);

  const loadWatchlist = () => {
    axios.get(`${API_BASE}/api/watchlist`).then((res) => {
      setWatchlist(res.data.watchlist || []);
    }).catch(() => setWatchlist([]));
  };

  const loadPortfolio = () => {
    axios.get(`${API_BASE}/api/portfolio`).then((res) => {
      setPositions(res.data.positions || []);
    }).catch(() => setPositions([]));
  };

  const loadLimitOrders = () => {
    axios.get(`${API_BASE}/api/limit-orders`).then((res) => {
      setLimitOrders(res.data.limit_orders || []);
    }).catch(() => setLimitOrders([]));
  };

  useEffect(() => {
    loadWatchlist();
    loadPortfolio();
    loadLimitOrders();
  }, []);

  useEffect(() => {
    if (initialSymbol && initialSymbol.trim()) {
      setSymbol(initialSymbol.trim().toUpperCase());
      onConsumeSymbol?.();
    }
  }, [initialSymbol]);

  useEffect(() => {
    if (!symbol.trim()) {
      setQuote(null);
      return;
    }
    setQuoteLoading(true);
    setQuote(null);
    axios
      .get(`${API_BASE}/api/quote/${encodeURIComponent(symbol.trim().toUpperCase())}`)
      .then((res) => setQuote(res.data))
      .catch(() => setQuote(null))
      .finally(() => setQuoteLoading(false));
  }, [symbol]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    const sym = symbol.trim().toUpperCase();
    const qty = parseFloat(quantity);
    if (!sym || !qty || qty <= 0) {
      setError("Enter a valid symbol and quantity.");
      return;
    }
    if (orderType === "limit") {
      const lp = parseFloat(limitPrice);
      if (!Number.isFinite(lp) || lp <= 0) {
        setError("Enter a valid limit price.");
        return;
      }
      if (side === "sell" && qty > maxSell) {
        setError("Insufficient shares to sell.");
        return;
      }
    } else {
      if (!quote || quote.price == null) {
        setError("Could not get price. Check symbol and try again.");
        return;
      }
      if (side === "sell" && qty > maxSell) {
        setError("Insufficient shares to sell.");
        return;
      }
    }
    setLoading(true);
    try {
      const body = { symbol: sym, side, quantity: qty };
      if (orderType === "limit") body.order_type = "limit";
      if (orderType === "limit") body.limit_price = parseFloat(limitPrice);
      const res = await axios.post(`${API_BASE}/api/order`, body);
      setSuccess(res.data.message);
      setQuantity("");
      setLimitPrice("");
      loadPortfolio();
      loadLimitOrders();
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Order failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelLimit = (id) => {
    axios.delete(`${API_BASE}/api/limit-orders/${id}`).then(() => loadLimitOrders()).catch(() => {});
  };

  const positionForSymbol = positions.find((p) => p.symbol === symbol.trim().toUpperCase());
  const maxSell = positionForSymbol ? parseFloat(positionForSymbol.quantity) : 0;
  const estTotal = orderType === "limit" && quantity && limitPrice
    ? parseFloat(quantity) * parseFloat(limitPrice)
    : quote && quantity ? parseFloat(quantity) * quote.price : 0;
  const canSubmitMarket = quote && quantity && parseFloat(quantity) > 0 && (side !== "sell" || parseFloat(quantity) <= maxSell);
  const canSubmitLimit = symbol.trim() && quantity && parseFloat(quantity) > 0 && limitPrice && parseFloat(limitPrice) > 0 && (side !== "sell" || parseFloat(quantity) <= maxSell);
  const canSubmit = orderType === "market" ? canSubmitMarket : canSubmitLimit;

  const pendingCount = limitOrders.filter((o) => o.status === "pending").length;

  return (
    <div className="trade-page">
      <header className="page-header">
        <h1>Trade</h1>
        <p className="subtitle">Paper trading — place market or limit orders. No real money is used.</p>
      </header>

      <div className="row g-4">
        {/* Order ticket */}
        <div className="col-lg-5">
          <div className="trade-order-ticket">
            <div className="ticket-header">Order ticket</div>
            <div className="ticket-body">
              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label className="form-label">Symbol</label>
                  <div className="symbol-input-wrap">
                    <input
                      type="text"
                      className="form-control text-uppercase"
                      placeholder="e.g. AAPL, MSFT"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value)}
                      list="watchlist-symbols"
                      autoComplete="off"
                    />
                    <datalist id="watchlist-symbols">
                      {watchlist.map((w) => (
                        <option key={w.id} value={w.symbol} />
                      ))}
                    </datalist>
                  </div>
                </div>

                <div className="mb-3">
                  <label className="form-label">Side</label>
                  <div className="side-toggle">
                    <button
                      type="button"
                      className={`btn btn-buy ${side === "buy" ? "active" : "outline"}`}
                      onClick={() => setSide("buy")}
                    >
                      <FaArrowUp className="me-1" /> Buy
                    </button>
                    <button
                      type="button"
                      className={`btn btn-sell ${side === "sell" ? "active" : "outline"}`}
                      onClick={() => setSide("sell")}
                      disabled={maxSell <= 0}
                      title={maxSell <= 0 ? "No position to sell" : ""}
                    >
                      <FaArrowDown className="me-1" /> Sell
                    </button>
                  </div>
                  {side === "sell" && positionForSymbol && (
                    <p className="trade-position-hint">You have {maxSell} share{maxSell !== 1 ? "s" : ""}.</p>
                  )}
                </div>

                <div className="mb-3">
                  <label className="form-label">Order type</label>
                  <select
                    className="form-select trade-order-type-select"
                    value={orderType}
                    onChange={(e) => setOrderType(e.target.value)}
                  >
                    <option value="market">Market</option>
                    <option value="limit">Limit</option>
                  </select>
                </div>

                {orderType === "limit" && (
                  <div className="mb-3">
                    <label className="form-label">Limit price</label>
                    <input
                      type="number"
                      className="form-control"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      value={limitPrice}
                      onChange={(e) => setLimitPrice(e.target.value)}
                    />
                    <p className="trade-position-hint">Buy when price ≤ limit; sell when price ≥ limit.</p>
                  </div>
                )}

                <div className="mb-3">
                  <label className="form-label">Quantity</label>
                  <input
                    type="number"
                    className="form-control"
                    min="0.0001"
                    step="any"
                    placeholder="0"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                  />
                </div>

                {(quote || (orderType === "limit" && limitPrice)) && (quantity && parseFloat(quantity) > 0) && (
                  <div className="order-summary">
                    {quote && (
                      <div className="order-summary-row">
                        <span className="label">Market price</span>
                        <span className="value">{formatMoney(quote.price)}</span>
                      </div>
                    )}
                    {orderType === "limit" && limitPrice && (
                      <div className="order-summary-row">
                        <span className="label">Limit price</span>
                        <span className="value">{formatMoney(parseFloat(limitPrice))}</span>
                      </div>
                    )}
                    <div className="order-summary-row">
                      <span className="label">Est. total</span>
                      <span className="value">{formatMoney(estTotal)}</span>
                    </div>
                  </div>
                )}

                {quoteLoading && (
                  <p className="small text-muted mb-2">Loading quote…</p>
                )}

                {error && (
                  <div className="alert alert-danger trade-alert mb-3" role="alert">
                    {error}
                  </div>
                )}
                {success && (
                  <div className="alert alert-success trade-alert mb-3" role="alert">
                    {success}
                  </div>
                )}

                <button
                  type="submit"
                  className={`btn btn-submit ${side === "buy" ? "btn-buy" : "btn-sell"}`}
                  disabled={loading || !canSubmit}
                >
                  {loading
                    ? "Placing order…"
                    : orderType === "limit"
                      ? `Place limit ${side} order`
                      : `${side === "buy" ? "Buy" : "Sell"} ${symbol || "—"}`
                  }
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Quote & open orders */}
        <div className="col-lg-7">
          <div className="trade-quote-card">
            <div className="quote-header">
              <FaChartLine className="me-1" /> Live quote
            </div>
            <div className="quote-body">
              {!symbol.trim() ? (
                <div className="trade-quote-empty">Enter a symbol to see price and details.</div>
              ) : quoteLoading ? (
                <div className="trade-quote-empty">Loading…</div>
              ) : quote ? (
                <>
                  <div className="quote-price">{formatMoney(quote.price)}</div>
                  {quote.shortName && <div className="quote-name">{quote.shortName}</div>}
                  <div className="d-flex align-items-center gap-2 mt-1">
                    <span className="fw-bold text-uppercase" style={{ fontSize: "0.875rem" }}>{quote.symbol}</span>
                    {quote.currency && <span className="text-muted small">· {quote.currency}</span>}
                  </div>
                  <div className="quote-meta">
                    {quote.previousClose != null && (
                      <span className="quote-meta-item">
                        Prev close <strong>{formatMoney(quote.previousClose)}</strong>
                      </span>
                    )}
                  </div>
                </>
              ) : (
                <div className="trade-quote-empty">No quote found for this symbol.</div>
              )}
            </div>
          </div>

          <div className="trade-limit-orders">
            <div className="orders-header">
              <span>Open limit orders</span>
              {pendingCount > 0 && (
                <span className="badge bg-secondary">{pendingCount} pending</span>
              )}
            </div>
            {limitOrders.length === 0 ? (
              <div className="trade-quote-empty py-4">No limit orders. Place a limit order above.</div>
            ) : (
              <>
                <div className="orders-table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th className="text-end">Qty</th>
                        <th className="text-end">Limit</th>
                        <th>Status</th>
                        <th className="text-end"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {limitOrders.map((o) => (
                        <tr key={o.id}>
                          <td><strong>{o.symbol}</strong></td>
                          <td>
                            <span className={o.side === "buy" ? "badge-buy" : "badge-sell"}>
                              {o.side}
                            </span>
                          </td>
                          <td className="text-end">{parseFloat(o.quantity)}</td>
                          <td className="text-end">{formatMoney(parseFloat(o.limit_price))}</td>
                          <td>
                            <span className={o.status === "pending" ? "badge-pending" : "badge-filled"}>
                              {o.status}
                            </span>
                          </td>
                          <td className="text-end">
                            {o.status === "pending" && (
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-danger btn-cancel"
                                onClick={() => handleCancelLimit(o.id)}
                                title="Cancel order"
                              >
                                <FaTimes className="me-1" /> Cancel
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="orders-footer">
                  Limit orders are evaluated when you open Portfolio; they fill when the market price reaches your limit.
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
