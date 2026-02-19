"""Ensemble and multi-step future prediction module."""
import numpy as np
import pandas as pd
from algorithms.base import get_data, result_dict
from algorithms.features import build_lag_features
import datetime
from utils.logger import logger

def clean_symbol(symbol):
    """Strip $ and whitespace."""
    return (symbol or "").strip().upper().replace("$", "")

class EnsemblePredictor:
    def __init__(self, algorithms_registry=None):
        self.registry = algorithms_registry
        self.feature_names = None

    def predict_recursive(self, model, last_window, steps, n_lags=5):
        """
        Predict future steps recursively using predicted values as future features.
        Only works for models that use simple lagged features.
        """
        predictions = []
        current_window = list(last_window)  # list of last n_lags values
        
        # Ensure we have feature names
        if self.feature_names is None:
            self.feature_names = [f"lag_{i}" for i in range(1, n_lags + 1)] + ["returns"]

        for _ in range(steps):
            # Construct features: lags 1 to n_lags and a simple 'returns' feature
            lags = current_window[::-1] # Most recent first
            
            # Calculate a simple return
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
        for algo_id in selected_algos:
            try:
                if algo_id == "lstm":
                    from algorithms.lstm import (
                        build_sequences,
                        _get_keras_model,
                        predict_future_steps,
                        SEQ_LEN as lstm_seq_len,
                    )
                    series = df["Close"]
                    min_v = float(series.min())
                    max_v = float(series.max())
                    rng_v = max_v - min_v if max_v > min_v else 1.0
                    scaled_series = (series - min_v) / rng_v
                    
                    X, y, _ = build_sequences(scaled_series, lstm_seq_len)
                    if X is not None and len(X) >= 20:
                        model = _get_keras_model(lstm_seq_len)
                        model.fit(X, y, epochs=30, batch_size=min(32, len(X)), verbose=0)
                        last_prices = df["Close"].values[-lstm_seq_len:]
                        preds = predict_future_steps(model, last_prices, steps, lstm_seq_len, min_val=min_v, range_val=rng_v)
                        results[algo_id] = [float(p) for p in preds]
                        all_preds.append(results[algo_id])
                    continue

                # For classical ML models, we use a shared logic
                model = None
                if algo_id == "linear_regression":
                    from sklearn.linear_model import LinearRegression
                    model = LinearRegression()
                elif algo_id == "random_forest":
                    from sklearn.ensemble import RandomForestRegressor
                    model = RandomForestRegressor(n_estimators=100)
                elif algo_id == "xgboost":
                    from xgboost import XGBRegressor
                    model = XGBRegressor()
                elif algo_id == "gradient_boosting":
                    from sklearn.ensemble import GradientBoostingRegressor
                    model = GradientBoostingRegressor()
                
                if model:
                    X, y, _ = build_lag_features(df["Close"], n_lags=n_lags)
                    if X is not None:
                        model.fit(X, y)
                        preds = self.predict_recursive(model, df["Close"].values[-n_lags:], steps, n_lags)
                        results[algo_id] = [float(p) for p in preds]
                        all_preds.append(results[algo_id])
            except Exception as e:
                logger.warning(f"Algo {algo_id} future prediction failed: {e}")

        if not all_preds:
            return {"error": f"Insufficient data to train models for {source}. Try a longer date range."}

        # Majority Voting for Trend
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
        total_up_votes = sum(1 for v in voting_results if v["trend"] == "Up")
        total_days = len(voting_results)
        ratio = total_up_votes / total_days if total_days > 0 else 0.5
        
        if ratio > 0.7:
            recommendation = "Strong Buy"
        elif ratio > 0.55:
            recommendation = "Buy"
        elif ratio < 0.3:
            recommendation = "Strong Sell"
        elif ratio < 0.45:
            recommendation = "Sell"
        else:
            recommendation = "Neutral / Hold"

        # Fetch "Actual" future data for comparison if it exists
        actual_compare_values = [None] * steps
        response_dates = [str(d.date()) for d in future_dates]
        
        try:
            today = datetime.datetime.now()
            if last_date.date() < today.date():
                compare_config = {
                    "startDate": str(last_date + pd.Timedelta(days=1)),
                    "endDate": str(today.date())
                }
                df_actual = get_data(compare_config, source)
                
                if df_actual is not None and not df_actual.empty:
                    # Align actual data with projected business days
                    actual_mapped = []
                    for fd in future_dates:
                        if fd in df_actual.index:
                            actual_mapped.append(float(df_actual.loc[fd, "Close"]))
                        else:
                            actual_mapped.append(None)
                    
                    # If we have actual data beyond the prediction length, we could extend
                    # but for now we'll stick to 'steps' length for simplicity in the UI chart
                    actual_compare_values = actual_mapped
        except Exception as e:
            logger.exception("Error fetching actual comparison: %s", e)

        return {
            "dates": response_dates,
            "predictions": results,
            "voting": voting_results,
            "recommendation": recommendation,
            "actual_future": actual_compare_values,
            "historical": {
                "dates": [str(d.date()) for d in df.index],
                "prices": [float(p) for p in df["Close"].values]
            }
        }

def run_future_prediction(data_config, source, steps=7, algorithms=None, registry=None):
    predictor = EnsemblePredictor(registry)
    return predictor.run_ensemble(data_config, source, steps, algorithms)
