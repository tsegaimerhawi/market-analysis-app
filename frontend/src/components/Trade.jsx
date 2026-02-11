import React, { useState, useEffect } from "react";
import axios from "axios";
import { FaArrowUp, FaArrowDown } from "react-icons/fa";

const API_BASE = "http://localhost:5000";

function formatMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(n);
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
  const totalCost = quote && quantity ? parseFloat(quantity) * (orderType === "limit" ? parseFloat(limitPrice) || quote.price : quote.price) : 0;
  const canSubmitMarket = quote && quantity && parseFloat(quantity) > 0 && (side !== "sell" || parseFloat(quantity) <= maxSell);
  const canSubmitLimit = symbol.trim() && quantity && parseFloat(quantity) > 0 && limitPrice && parseFloat(limitPrice) > 0 && (side !== "sell" || parseFloat(quantity) <= maxSell);
  const canSubmit = orderType === "market" ? canSubmitMarket : canSubmitLimit;

  return (
    <div className="trade">
      <h1 className="mb-4">Trade</h1>
      <p className="text-muted mb-4">Paper trading: buy or sell stocks using the current market price. No real money is used.</p>

      <div className="row">
        <div className="col-lg-5 mb-4">
          <div className="card shadow-sm border-0">
            <div className="card-body">
              <h5 className="card-title mb-4">Place order</h5>
              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label className="form-label">Symbol</label>
                  <input
                    type="text"
                    className="form-control text-uppercase"
                    placeholder="e.g. AAPL"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    list="watchlist-symbols"
                  />
                  <datalist id="watchlist-symbols">
                    {watchlist.map((w) => (
                      <option key={w.id} value={w.symbol} />
                    ))}
                  </datalist>
                </div>

                <div className="mb-3">
                  <label className="form-label">Side</label>
                  <div className="d-flex gap-2">
                    <button
                      type="button"
                      className={`btn flex-grow-1 ${side === "buy" ? "btn-success" : "btn-outline-success"}`}
                      onClick={() => setSide("buy")}
                    >
                      <FaArrowUp className="me-1" /> Buy
                    </button>
                    <button
                      type="button"
                      className={`btn flex-grow-1 ${side === "sell" ? "btn-danger" : "btn-outline-danger"}`}
                      onClick={() => setSide("sell")}
                      disabled={maxSell <= 0}
                      title={maxSell <= 0 ? "No position to sell" : ""}
                    >
                      <FaArrowDown className="me-1" /> Sell
                    </button>
                  </div>
                  {side === "sell" && positionForSymbol && (
                    <small className="text-muted">You have {maxSell} share(s).</small>
                  )}
                </div>

                <div className="mb-3">
                  <label className="form-label">Order type</label>
                  <select className="form-select" value={orderType} onChange={(e) => setOrderType(e.target.value)}>
                    <option value="market">Market</option>
                    <option value="limit">Limit</option>
                  </select>
                </div>

                {orderType === "limit" && (
                  <div className="mb-3">
                    <label className="form-label">Limit price ($)</label>
                    <input
                      type="number"
                      className="form-control"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      value={limitPrice}
                      onChange={(e) => setLimitPrice(e.target.value)}
                    />
                    <small className="text-muted">Buy executes when price ≤ limit; sell when price ≥ limit.</small>
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

                {(quote || (orderType === "limit" && limitPrice)) && (
                  <div className="mb-3 p-2 bg-light rounded">
                    {quote && (
                      <div className="d-flex justify-content-between">
                        <span className="text-muted">Market price</span>
                        <strong>{formatMoney(quote.price)}</strong>
                      </div>
                    )}
                    {orderType === "limit" && quantity && parseFloat(quantity) > 0 && limitPrice && (
                      <div className="d-flex justify-content-between mt-1">
                        <span className="text-muted">Est. total (at limit)</span>
                        <strong>{formatMoney(parseFloat(quantity) * parseFloat(limitPrice))}</strong>
                      </div>
                    )}
                    {orderType === "market" && quantity && parseFloat(quantity) > 0 && (
                      <div className="d-flex justify-content-between mt-1">
                        <span className="text-muted">Est. total</span>
                        <strong>{formatMoney(totalCost)}</strong>
                      </div>
                    )}
                  </div>
                )}

                {quoteLoading && <p className="small text-muted">Loading quote…</p>}

                {error && (
                  <div className="alert alert-danger py-2 mb-3" role="alert">
                    {error}
                  </div>
                )}
                {success && (
                  <div className="alert alert-success py-2 mb-3" role="alert">
                    {success}
                  </div>
                )}

                <button
                  type="submit"
                  className={`btn w-100 ${side === "buy" ? "btn-success" : "btn-danger"}`}
                  disabled={loading || !canSubmit}
                >
                  {loading ? "Placing…" : orderType === "limit" ? "Place limit order" : (side === "buy" ? "Buy" : "Sell")} {symbol || "—"}
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="card shadow-sm border-0">
            <div className="card-body">
              <h5 className="card-title mb-3">Quote</h5>
              {!symbol.trim() ? (
                <p className="text-muted mb-0">Enter a symbol to see live price.</p>
              ) : quoteLoading ? (
                <p className="text-muted mb-0">Loading…</p>
              ) : quote ? (
                <dl className="row mb-0">
                  <dt className="col-sm-4">Symbol</dt>
                  <dd className="col-sm-8"><strong>{quote.symbol}</strong></dd>
                  <dt className="col-sm-4">Price</dt>
                  <dd className="col-sm-8">{formatMoney(quote.price)}</dd>
                  {quote.previousClose != null && (
                    <>
                      <dt className="col-sm-4">Previous close</dt>
                      <dd className="col-sm-8">{formatMoney(quote.previousClose)}</dd>
                    </>
                  )}
                  {quote.shortName && (
                    <>
                      <dt className="col-sm-4">Name</dt>
                      <dd className="col-sm-8">{quote.shortName}</dd>
                    </>
                  )}
                </dl>
              ) : (
                <p className="text-muted mb-0">No quote found for this symbol.</p>
              )}
            </div>
          </div>

          {limitOrders.length > 0 && (
            <div className="card shadow-sm border-0 mt-4">
              <div className="card-body">
                <h5 className="card-title mb-3">Limit orders</h5>
                <div className="table-responsive">
                  <table className="table table-sm">
                    <thead className="table-light">
                      <tr>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th className="text-end">Qty</th>
                        <th className="text-end">Limit</th>
                        <th>Status</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {limitOrders.map((o) => (
                        <tr key={o.id}>
                          <td><strong>{o.symbol}</strong></td>
                          <td><span className={`badge ${o.side === "buy" ? "bg-success" : "bg-danger"}`}>{o.side}</span></td>
                          <td className="text-end">{parseFloat(o.quantity)}</td>
                          <td className="text-end">{formatMoney(parseFloat(o.limit_price))}</td>
                          <td><span className={`badge ${o.status === "pending" ? "bg-warning text-dark" : "bg-secondary"}`}>{o.status}</span></td>
                          <td>
                            {o.status === "pending" && (
                              <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => handleCancelLimit(o.id)}>Cancel</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="small text-muted mb-0">Limit orders are checked when you open Portfolio; they execute when the market price reaches your limit.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
