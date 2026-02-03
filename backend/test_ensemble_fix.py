import sys
import os
import pandas as pd
import numpy as np

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from algorithms.ensemble import EnsemblePredictor, clean_symbol

def test_clean_symbol():
    assert clean_symbol("$AAPL") == "AAPL"
    assert clean_symbol("  msft  ") == "MSFT"

def test_recursive_prediction_logic():
    # Mock model
    class MockModel:
        def predict(self, df):
            # return 1.01 * last lag
            return [df.iloc[0, 0] * 1.01]
    
    predictor = EnsemblePredictor(None)
    predictor.feature_names = ["lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "returns"]
    last_window = [100.0, 101.0, 102.0, 103.0, 104.0] # 5 lags
    steps = 3
    
    # We need to set feature_names manually for test or use run_ensemble
    preds = predictor.predict_recursive(MockModel(), last_window, steps)
    
    assert len(preds) == steps
    assert preds[0] > 104.0

if __name__ == "__main__":
    test_clean_symbol()
    test_recursive_prediction_logic()
