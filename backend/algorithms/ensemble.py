"""Ensemble and multi-step future prediction module."""
import numpy as np
import pandas as pd
from algorithms.base import get_data, result_dict
from algorithms.features import build_lag_features
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from xgboost import XGBRegressor
import datetime
from utils.logger import logger

def clean_symbol(symbol):
    """Strip $ and whitespace."""
    return (symbol or "").strip().upper().replace("$", "")

class EnsemblePredictor:
    def __init__(self, algorithms_registry):
        self.registry = algorithms_registry

    def predict_recursive(self, model, last_window, steps, n_lags=5):
        """
        Predict future steps recursively using predicted values as future features.
        Only works for models that use simple lagged features.
        """
        predictions = []
        current_window = list(last_window)  # list of last n_lags values
        
        for _ in range(steps):
            # Construct features: lags 1 to n_lags and a simple 'returns' feature (dummy for now)
            # Existing build_lag_features: df[f"lag_{i}"] = df["y"].shift(i), df["returns"] = df["y"].pct_change().shift(1)
            # For iteration, we just need the last n_lags.
            
            # Simple feature vector: [lag_1, lag_2, ..., lag_n, returns]
            # lag_1 is current_window[-1], lag_2 is current_window[-2], etc.
            lags = current_window[::-1] # Most recent first
            
            # Calculate a simple return if possible
            ret = 0
            if len(current_window) >= 2:
                ret = (current_window[-1] - current_window[-2]) / current_window[-2] if current_window[-2] != 0 else 0
            
            # Create DataFrame for prediction to maintain feature names
            features_df = pd.DataFrame([lags + [ret]], columns=self.feature_names)
            
            # Predict
            pred = float(model.predict(features_df)[0])
            predictions.append(pred)
            
            # Update window
            current_window.append(pred)
            current_window.pop(0)
            
        return predictions

    def get_future_dates(self, last_date, steps):
        """Generate future dates (business days)."""
        return pd.date_range(start=last_date + pd.Timedelta(days=1), periods=steps, freq='B')

    def run_ensemble(self, data_config, source, steps, selected_algos=None):
        source = clean_symbol(source)
        df = get_data(data_config, source)
        if df is None:
            return {"error": f"Failed to load data for {source}. Please check the symbol and date range."}
        
        last_date = df.index[-1]
        last_close = df["Close"].values[-1]
        n_lags = 5
        self.feature_names = [f"lag_{i}" for i in range(1, n_lags + 1)] + ["returns"]
        
        future_dates = self.get_future_dates(last_date, steps)
        
        results = {}
        all_preds = []
        
        if not selected_algos:
            selected_algos = ["linear_regression", "random_forest", "xgboost"]

        # For this ensemble, we handle models we know how to iterate
        # We'll use a simplified version of the model training here or use the registry if they support steps
        for algo_id in selected_algos:
            if algo_id == "linear_regression":
                from sklearn.linear_model import LinearRegression as LR
                model = LR()
                X, y, _ = build_lag_features(df["Close"], n_lags=n_lags)
                if X is not None:
                    model.fit(X, y)
                    preds = self.predict_recursive(model, df["Close"].values[-n_lags:], steps, n_lags)
                    results[algo_id] = preds
                    all_preds.append(preds)
            elif algo_id == "random_forest":
                from sklearn.ensemble import RandomForestRegressor as RF
                model = RF(n_estimators=100)
                X, y, _ = build_lag_features(df["Close"], n_lags=n_lags)
                if X is not None:
                    model.fit(X, y)
                    preds = self.predict_recursive(model, df["Close"].values[-n_lags:], steps, n_lags)
                    results[algo_id] = preds
                    all_preds.append(preds)
            elif algo_id == "xgboost":
                from xgboost import XGBRegressor as XGB
                model = XGB()
                X, y, _ = build_lag_features(df["Close"], n_lags=n_lags)
                if X is not None:
                    model.fit(X, y)
                    preds = self.predict_recursive(model, df["Close"].values[-n_lags:], steps, n_lags)
                    results[algo_id] = [float(p) for p in preds]
                    all_preds.append([float(p) for p in preds])
            elif algo_id == "lstm":
                try:
                    from algorithms.lstm import (
                        build_sequences,
                        _get_keras_model,
                        predict_future_steps,
                        SEQ_LEN as lstm_seq_len,
                    )
                    series = df["Close"]
                    X, y, _ = build_sequences(series, lstm_seq_len)
                    if X is not None and len(X) >= 20:
                        model = _get_keras_model(lstm_seq_len)
                        model.fit(X, y, epochs=30, batch_size=min(32, len(X)), verbose=0)
                        last_prices = df["Close"].values[-lstm_seq_len:]
                        preds = predict_future_steps(model, last_prices, steps, lstm_seq_len)
                        results[algo_id] = [float(p) for p in preds]
                        all_preds.append([float(p) for p in preds])
                except Exception as e:
                    logger.warning("LSTM future prediction skipped: %s", e)

        if not all_preds:
            return {"error": f"Insufficient data to train models for {source}. Try a longer date range."}

        # Majority Voting for Trend
        # Trend is Up (1) if pred[t] > pred[t-1] (or last_close for t=0), else Down (0)
        voting_results = []
        
        for t in range(steps):
            votes_up = 0
            for m in range(len(all_preds)):
                prev_val = float(last_close) if t == 0 else float(all_preds[m][t-1])
                if float(all_preds[m][t]) > prev_val:
                    votes_up += 1
            
            majority_trend = "Up" if votes_up > len(all_preds) / 2 else "Down"
            voting_results.append({
                "date": str(future_dates[t].date()),
                "trend": majority_trend,
                "confidence": round(float(votes_up / len(all_preds) * 100), 2)
            })

        # Consensus Recommendation based on Majority Vote
        # Look at the overall trend (sum of daily votes)
        total_up_votes = sum(1 for v in voting_results if v["trend"] == "Up")
        total_days = len(voting_results)
        
        if total_up_votes / total_days > 0.7:
            recommendation = "Strong Buy"
        elif total_up_votes / total_days > 0.55:
            recommendation = "Buy"
        elif total_up_votes / total_days < 0.3:
            recommendation = "Strong Sell"
        elif total_up_votes / total_days < 0.45:
            recommendation = "Sell"
        else:
            recommendation = "Neutral / Hold"

        # Fetch "Actual" future data for comparison if it exists
        actual_compare = []
        try:
            # We need to fetch data after last_date up to "today".
            # This allows the user to see actual performance even if the prediction window has passed.
            today = datetime.datetime.now()
            compare_config = {
                "startDate": str(last_date + pd.Timedelta(days=1)),
                "endDate": str(today.date())
            }
            df_actual = get_data(compare_config, source)
            
            # Identify all unique dates from future_dates and df_actual to build a full comparison series
            # But the primary goal is to align with the predictions and possibly extend them.
            
            # Let's collect ALL dates for the return dict
            all_comparison_dates = list(future_dates)
            if df_actual is not None:
                for d in df_actual.index:
                    if d not in all_comparison_dates:
                        all_comparison_dates.append(d)
            
            all_comparison_dates = sorted(list(set(all_comparison_dates)))
            
            # Build the actual_future series for ALL these dates
            actual_compare_values = []
            final_dates = []
            for fd in all_comparison_dates:
                val = None
                if df_actual is not None and fd in df_actual.index:
                    val = float(df_actual.loc[fd, "Close"])
                
                # Only include dates that are in prediction OR have actual data
                if fd in future_dates or val is not None:
                    actual_compare_values.append(val)
                    final_dates.append(str(fd.date()))

            # Update future_dates to include any extended actual data for the chart
            response_dates = final_dates
        except Exception as e:
            logger.exception("Error fetching actual comparison: %s", e)
            actual_compare_values = [None] * steps
            response_dates = [str(d.date()) for d in future_dates]

        return {
            "dates": response_dates,
            "predictions": results,
            "voting": voting_results,
            "recommendation": recommendation,
            "actual_future": actual_compare_values,
            "historical": {
                "dates": [str(d.date()) for d in df.index[-20:]],
                "prices": [float(p) for p in df["Close"].values[-20:]]
            }
        }

def run_future_prediction(data_config, source, steps=7, algorithms=None):
    predictor = EnsemblePredictor(None)
    return predictor.run_ensemble(data_config, source, steps, algorithms)
