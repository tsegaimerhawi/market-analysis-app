"""Ensemble and multi-step future prediction module."""
import numpy as np
import pandas as pd
from algorithms.base import get_data, result_dict
from algorithms.features import build_lag_features
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
import datetime

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
            
            features = np.array(lags + [ret]).reshape(1, -1)
            
            # Predict
            pred = model.predict(features)[0]
            predictions.append(pred)
            
            # Update window
            current_window.append(pred)
            current_window.pop(0)
            
        return predictions

    def get_future_dates(self, last_date, steps):
        """Generate future dates (business days)."""
        return pd.date_range(start=last_date + pd.Timedelta(days=1), periods=steps, freq='B')

    def run_ensemble(self, data_config, source, steps, selected_algos=None):
        df = get_data(data_config, source)
        if df is None:
            return {"error": "Failed to load data"}
        
        last_date = df.index[-1]
        last_close = df["Close"].values[-1]
        n_lags = 5
        last_window = df["Close"].values[-n_lags-1:].tolist() # Get enough for current and lags
        
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
                    results[algo_id] = preds
                    all_preds.append(preds)

        if not all_preds:
            return {"error": "No valid models selected/trained"}

        # Majority Voting for Trend
        # Trend is Up (1) if pred[t] > pred[t-1] (or last_close for t=0), else Down (0)
        voting_results = []
        all_preds_matrix = np.array(all_preds) # (num_models, steps)
        
        for t in range(steps):
            votes_up = 0
            for m in range(len(all_preds)):
                prev_val = last_close if t == 0 else all_preds[m][t-1]
                if all_preds[m][t] > prev_val:
                    votes_up += 1
            
            majority_trend = "Up" if votes_up > len(all_preds) / 2 else "Down"
            voting_results.append({
                "date": str(future_dates[t].date()),
                "trend": majority_trend,
                "confidence": round(votes_up / len(all_preds) * 100, 2)
            })

        return {
            "dates": [str(d.date()) for d in future_dates],
            "predictions": results,
            "voting": voting_results,
            "historical": {
                "dates": [str(d.date()) for d in df.index[-20:]],
                "prices": df["Close"].values[-20:].tolist()
            }
        }

def run_future_prediction(data_config, source, steps=7, algorithms=None):
    predictor = EnsemblePredictor(None)
    return predictor.run_ensemble(data_config, source, steps, algorithms)
