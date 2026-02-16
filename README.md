# Market Analysis App

A web-based platform to analyze stock data using **10 prediction algorithms**. Build a **watchlist** of companies, view **full company info** (via yfinance), and run analysis by selecting a company and date range.

## Features

- **Watchlist** – Save companies by ticker symbol (e.g. AAPL, AMCR). Add/remove from the Watchlist view.
- **Company info** – For any symbol in your watchlist, view full company data from the system (yfinance: sector, industry, market cap, P/E, dividends, business summary, etc.).
- **Stock analysis** – Choose a company from your watchlist, set start/end date, select algorithms, and compare results (MAE, RMSE, MAPE, direction accuracy) and charts.
- **Future Prediction (New!)** – Project future stock prices up to 30 days ahead using an ensemble of models (Linear Regression, Random Forest, XGBoost).
- **Ensemble Majority Voting** – View a consensus-based market recommendation (Buy/Sell/Hold) derived from the majority vote of independent models.
- **Ground Truth Visualization** – Compare predictions against actual market data in real-time. If you select a past date, the app overlays the "Actual" price line to verify model accuracy.
- **Paper trading** – **Portfolio** and **Trade** views let you buy and sell stocks with simulated cash (default $100,000). Orders use live quotes; positions and order history are stored in SQLite.
- **Trading Agent** – Auto-trading with a hybrid ensemble: LSTM (40%), XGBoost (20%), Sentiment LLM (30%), Macro LLM (10%) via OpenRouter. Turn on/off, view reasoning and history. Set `OPEN_ROUTER_TRADER_API_KEY` (or `OPEN_ROUTER_API_KEY`) for LLM agents.

## Project structure

- **backend/**
  - `db.py` – SQLite DB: watchlist, account (paper cash), portfolio (positions), orders.
  - `main.py` – API: `/api/watchlist`, `/api/company/<symbol>`, `/api/compare`, `/api/predict-future`, `/api/portfolio`, `/api/quote/<symbol>`, `/api/order`.
  - `services/company_service.py` – yfinance integration and full company info.
  - `algorithms/ensemble.py` – Multi-model ensemble and recursive prediction logic.
  - `algorithms/` – 10 prediction modules (all accept symbol or CSV path).
- **frontend/**
  - `Watchlist.jsx` – Add/remove companies, view company info, **Trade** quick action.
  - `FuturePrediction.js` – Ensemble dashboard with charts and voting results.
  - `CompanyInfo.jsx` – Full company info panel (everything from yfinance).
  - `StockAnalysis.jsx` – Comparison view for baseline models.
  - `Portfolio.jsx` – Paper portfolio: cash, positions (with live value), order history.
  - `Trade.jsx` – Buy/sell form with live quote and position-aware sell.

## Run the app

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

API runs at `http://localhost:5001` (port 5001 avoids conflict with macOS AirPlay on 5000). The watchlist is stored in `backend/watchlist.db` (created on first run). Override with `PORT=5002 python main.py` if needed.

For the **Trading Agent** LLM layer (Sentiment + Macro), set your OpenRouter API key:

```bash
export OPEN_ROUTER_TRADER_API_KEY=your_key
# or
export OPEN_ROUTER_API_KEY=your_key
```

To receive **Telegram notifications** when the agent runs and has updates (buy/sell, stop-loss, take-profit), set your bot token and chat ID:

```bash
export TELEGRAM_HTTP_API_KEY=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
```

(Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot) or by starting a chat with your bot and calling `getUpdates` on the Bot API.)

For **real news headlines** (Sentiment agent): set `NEWS_API_KEY` (from [NewsAPI.org](https://newsapi.org)). For **macro data** (Macro agent): set `MACRO_API_KEY` or `ALPHA_VANTAGE_API_KEY`. If unset, stubs are used.

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
4. **Portfolio** – View paper cash balance, positions (with current market value and P&L), and recent orders.
5. **Trade** – Enter a symbol (or click **Trade** from the watchlist), choose Buy/Sell, quantity, and place a paper order at the current quote price.
