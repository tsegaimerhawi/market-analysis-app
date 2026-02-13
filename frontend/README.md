# Market Analysis App — Frontend

React frontend for the **Market Analysis App**: stock watchlist, multi-algorithm analysis, future predictions, and paper trading (portfolio, orders, limit orders).

## Tech stack

- **React** 19
- **Bootstrap 5** — layout and components
- **Recharts** — price and prediction charts
- **Axios** — API requests
- **react-icons** — UI icons

The app expects the [backend](../backend) API at `http://localhost:5001`. Start the backend before or with the frontend. (Port 5001 is used to avoid conflict with macOS AirPlay on 5000.)

## Project structure

```
src/
├── App.js                 # Root component
├── App.css
├── index.js
└── components/
    ├── Main.jsx            # Layout + view router
    ├── SideBar.jsx          # Navigation
    ├── Watchlist.jsx       # Add/remove companies, company info, Trade shortcut
    ├── CompanyInfo.jsx      # Full company details (yfinance)
    ├── StockAnalysis.jsx    # Algorithm comparison (MAE, RMSE, charts)
    ├── FuturePrediction.js  # Ensemble forecast, consensus, ground truth chart
    ├── Portfolio.jsx        # Cash, positions, P&L, orders, reset, deposit/withdraw, export CSV
    ├── Trade.jsx            # Buy/sell (market + limit), quotes, pending limit orders
    ├── ScrapeArticles.jsx   # Article scraping UI
    ├── AlgorithmTutorials.jsx
    └── *.css
```

## Quick start

**1. Install dependencies**

```bash
npm install
```

**2. Start the backend** (from repo root)

```bash
cd backend
pip install -r requirements.txt
python main.py
```

API: `http://localhost:5001`

**3. Start the frontend**

```bash
npm start
```

App: [http://localhost:3000](http://localhost:3000)

## Available scripts

| Command | Description |
|--------|--------------|
| `npm start` | Development server at [http://localhost:3000](http://localhost:3000). Hot reload and lint in console. |
| `npm run build` | Production build into `build/`. Minified, hashed filenames. |
| `npm test` | Run tests in watch mode. |
| `npm run eject` | Eject Create React App (one-way; not required). |

## Features (frontend)

- **Watchlist** — Manage symbols; open company info or jump to Trade.
- **Stock Analysis** — Pick symbol, date range, and algorithms; compare metrics and charts.
- **Future Prediction** — Ensemble forecast, consensus recommendation, brushable chart with actuals.
- **Portfolio** — Cash, positions with live value and P&L, order history, deposit/withdraw, reset, export CSV.
- **Trade** — Market and limit orders, live quote, pending limit orders with cancel.
- **Algorithm Tutorials** — In-app docs for each model.

## Configuration

The API base URL is set in components as `http://localhost:5001`. To point to another host or port (e.g. production), set the `PORT` env when starting the backend and update the `API_BASE` constant in each component that uses it, or introduce a shared config/env variable.

## Learn more

- [Create React App docs](https://create-react-app.dev/docs/getting-started/)
- [React docs](https://react.dev/)
