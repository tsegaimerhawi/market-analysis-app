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
  - `main.py` – Entry point and background tasks.
  - `config.py` – Configuration management.
  - `routes/` – API blueprints (watchlist, company, portfolio, agent, etc.).
  - `db.py` – SQLite DB management.
  - `services/` – Business logic (company, news, macro).
  - `algorithms/` – Prediction modules.
- **frontend/**
  - `vite.config.js` – Vite configuration.
  - `src/` – React application using Vite.

## Run the app

### Using Docker (Highly Recommended)

The easiest way to run the entire stack is using Docker Compose:

```bash
docker-compose up --build
```

- Backend: `http://localhost:5001`
- Frontend: `http://localhost:80` (mapped from container 80)

### Manual Setup

#### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:3000`.

### Configuration

For the **Trading Agent** LLM layer (Sentiment + Macro), set your OpenRouter API key in `backend/.env`:

```bash
OPEN_ROUTER_API_KEY=your_key
```

To receive **Telegram notifications**, set your bot token and chat ID:

```bash
TELEGRAM_HTTP_API_KEY=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

For **real news headlines**: set `NEWS_API_KEY`. For **macro data**: set `MACRO_API_KEY`. If unset, stubs are used.
