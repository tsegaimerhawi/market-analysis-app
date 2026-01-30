# Market Analysis App

A web-based platform to analyze stock data using **10 prediction algorithms**. Build a **watchlist** of companies, view **full company info** (via yfinance), and run analysis by selecting a company and date range.

## Features

- **Watchlist** – Save companies by ticker symbol (e.g. AAPL, AMCR). Add/remove from the Watchlist view.
- **Company info** – For any symbol in your watchlist, view full company data from the system (yfinance: sector, industry, market cap, P/E, dividends, business summary, etc.).
- **Stock analysis** – Choose a company from your watchlist, set start/end date, select algorithms, and compare results (MAE, RMSE, MAPE, direction accuracy) and charts.
- **Future Prediction (New!)** – Project future stock prices up to 30 days ahead using an ensemble of models (Linear Regression, Random Forest, XGBoost).
- **Ensemble Majority Voting** – View a consensus-based market recommendation (Buy/Sell/Hold) derived from the majority vote of independent models.
- **Ground Truth Visualization** – Compare predictions against actual market data in real-time. If you select a past date, the app overlays the "Actual" price line to verify model accuracy.

## Project structure

- **backend/**
  - `db.py` – SQLite watchlist DB (add/remove/list companies).
  - `main.py` – API: `/api/watchlist`, `/api/company/<symbol>`, `/api/compare`, `/api/predict-future`.
  - `services/company_service.py` – yfinance integration and full company info.
  - `algorithms/ensemble.py` – Multi-model ensemble and recursive prediction logic.
  - `algorithms/` – 10 prediction modules (all accept symbol or CSV path).
- **frontend/**
  - `Watchlist.jsx` – Add/remove companies, view company info.
  - `FuturePrediction.js` – Ensemble dashboard with charts and voting results.
  - `CompanyInfo.jsx` – Full company info panel (everything from yfinance).
  - `StockAnalysis.jsx` – Comparison view for baseline models.

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
2. **Stock Analysis** – Select a company from the dropdown, set dates, choose algorithms, then **Compare algorithms**.
3. **Future Prediction** – Navigate to the **Future Prediction** tab. Select a company and a future date range. Click **Forecast** to view the ensemble consensus, individual model paths, and the majority decision recommendation. If data is available for that period, a "Ground Truth" line will appear for comparison.
