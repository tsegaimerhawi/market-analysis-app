# Feature ideas for Market Analysis App

Use this list to extend the app with more advanced trading and analysis features.

---

## Trading & portfolio

- **Limit and stop orders** – Place buy/sell orders that execute when price hits a target (limit) or stop level.
- **Order types** – Market (current), limit, stop-loss, stop-limit; optional time-in-force (day, GTC).
- **Multiple portfolios** – Named portfolios (e.g. “Growth”, “Dividends”) with separate cash and positions.
- **Reset paper account** – Button to reset cash to default (e.g. $100,000) and clear all positions/orders.
- **Deposit/withdraw (paper)** – Adjust cash balance without a trade for more realistic simulation.
- **Fractional shares** – Support decimal quantities (already supported in DB; ensure UI and validation allow it).
- **Dividends** – Credit paper cash when a held position pays a dividend (using yfinance dividend data).

---

## Broker integration (real trading)

- **Broker API** – Integrate with a broker API (e.g. Alpaca, TD Ameritrade, Interactive Brokers) for real orders.
- **Paper vs live mode** – Toggle between paper trading (current) and live trading with clear warnings.
- **Real portfolio sync** – Pull real positions and orders from the broker and show alongside or instead of paper.

---

## Alerts & automation

- **Price alerts** – Notify when a symbol crosses a price (e.g. email or in-app).
- **Prediction-based alerts** – Alert when the ensemble recommendation flips to Buy or Sell for a symbol.
- **Scheduled scans** – Run analysis or predictions on a schedule and store or email results.
- **Auto-trade (paper)** – Optional rules: e.g. “If ensemble says Buy and confidence > 70%, place a paper buy.”

---

## Analytics & reporting

- **Portfolio performance** – Total return, daily P&L, drawdown, simple benchmark comparison (e.g. S&P 500).
- **Trade log export** – Export orders and positions to CSV for tax or external analysis.
- **Charts** – Portfolio value over time; allocation pie (cash vs symbols); P&L by symbol.
- **Backtesting** – Replay historical “what if I had followed the model?” using past predictions vs actuals.

---

## UX & data

- **Real-time quotes** – WebSocket or short-interval polling for live price updates on Trade and Portfolio.
- **Symbol search** – Type-ahead search for symbols/names (beyond watchlist) in Trade and Analysis.
- **Keyboard shortcuts** – Quick keys for Trade (e.g. B/S for buy/sell), refresh portfolio, etc.
- **Dark mode** – Theme toggle for the whole app.
- **Mobile-friendly layout** – Responsive Trade and Portfolio for small screens.

---

## Prediction & models

- **Save prediction runs** – Store prediction results with timestamp and symbol; compare later to actuals.
- **Model confidence in Trade** – On Trade screen, show latest ensemble recommendation and confidence for the symbol.
- **Custom date ranges for backtest** – Run “what would the model have said on date X?” and compare to actual.
- **More assets** – Support ETFs, crypto, or forex if your data source (e.g. yfinance) supports it.

---

## Technical

- **User accounts** – Login so each user has their own watchlist and paper portfolio (e.g. JWT + SQLite or Postgres).
- **Environment config** – API base URL, default cash, feature flags via env vars or config file.
- **Tests** – Unit tests for `execute_buy` / `execute_sell`, API routes, and critical frontend flows.
- **Rate limiting** – Throttle quote and history requests to avoid hitting provider limits.

Pick any item above and implement step by step; the current codebase is structured so you can add these without a full rewrite.
