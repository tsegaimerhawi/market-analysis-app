# Market Analysis App

A web-based platform to analyze stock data using **10 prediction algorithms**. Build a **watchlist** of companies, view **full company info** (via yfinance), and run analysis by selecting a company and date range.

## Features

- **Watchlist** – Save companies by ticker symbol (e.g. AAPL, AMCR). Add/remove from the Watchlist view.
- **Company info** – For any symbol in your watchlist, view full company data from the system (yfinance: sector, industry, market cap, P/E, dividends, business summary, etc.).
- **Stock analysis** – Choose a company from your watchlist, set start/end date, select algorithms, and compare results (MAE, RMSE, MAPE, direction accuracy) and charts.
- **Data source** – Stock data is fetched with the **yfinance** Python library (Yahoo Finance); no CSV upload required for watchlist companies. (CSV upload is still supported for the compare endpoint if you send `dataFile` instead of `symbol`.)

## Project structure

- **backend/**
  - `db.py` – SQLite watchlist DB (add/remove/list companies).
  - `main.py` – API: `/api/watchlist`, `/api/company/<symbol>`, `/api/compare`, `/api/algorithms`.
  - `services/company_service.py` – yfinance: history (OHLCV) and full company info.
  - `algorithms/` – 10 prediction modules (all accept symbol or CSV path).
- **frontend/**
  - `Watchlist.jsx` – Add/remove companies, view company info.
  - `CompanyInfo.jsx` – Full company info panel (everything from yfinance).
  - `StockAnalysis.jsx` – Company dropdown (from watchlist), dates, algorithms, results table and chart.

## Run the app

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

API runs at `http://localhost:5000`. The watchlist is stored in `backend/watchlist.db` (created on first run).

### Frontend

```bash
cd frontend
npm install
npm start
```

App runs at `http://localhost:3000`.

### Usage

1. **Watchlist** – Add companies by symbol (e.g. AAPL, MSFT). Click **Company info** on any row to see full data from the system. Remove with **Remove**.
2. **Stock Analysis** – Select a company from the dropdown (your watchlist), set **Start date** and **End date**, choose algorithms, then **Compare algorithms**. View the results table and chart (actual vs predicted).
