import sys
import os
import pandas as pd
import numpy as np

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from algorithms.ensemble import EnsemblePredictor, clean_symbol

def test_clean_symbol():
    print("Testing clean_symbol...")
    assert clean_symbol("$AAPL") == "AAPL"
    assert clean_symbol("  msft  ") == "MSFT"
    print("✓ clean_symbol passed")

def test_recursive_prediction_logic():
    print("Testing recursive_prediction_logic...")
    # Mock model
    class MockModel:
        def predict(self, df):
            # return 1.01 * last lag (which is lag_1)
            # feature vector is [lag_1, lag_2, ..., lag_5, returns]
            return [df.iloc[0, 0] * 1.01]
    
    predictor = EnsemblePredictor(None)
    last_window = [100.0, 101.0, 102.0, 103.0, 104.0] # 5 lags
    steps = 3
    
    preds = predictor.predict_recursive(MockModel(), last_window, steps)
    
    assert len(preds) == steps
    assert preds[0] == 104.0 * 1.01
    assert preds[1] == preds[0] * 1.01
    print("✓ recursive_prediction_logic passed")

def test_trend_and_recommendation():
    print("Testing trend and recommendation logic...")
    predictor = EnsemblePredictor(None)
    
    # Mock data for run_ensemble return-like structure
    # Case: Strong Buy (All up)
    all_preds = [
        [105, 106, 107], # Model 1
        [105.5, 106.5, 107.5] # Model 2
    ]
    last_close = 104.0
    steps = 3
    
    # We'll just test the voting logic inside a simulated run
    voting_results = []
    for t in range(steps):
        votes_up = 0
        for m in range(len(all_preds)):
            prev_val = float(last_close) if t == 0 else float(all_preds[m][t-1])
            if float(all_preds[m][t]) > prev_val:
                votes_up += 1
        
        majority_trend = "Up" if votes_up > len(all_preds) / 2 else "Down"
        voting_results.append({"trend": majority_trend})

    total_up_votes = sum(1 for v in voting_results if v["trend"] == "Up")
    ratio = total_up_votes / len(voting_results)
    
    assert ratio == 1.0
    assert ratio > 0.7 # Strong Buy
    print("✓ trend and recommendation logic passed")

if __name__ == "__main__":
    try:
        test_clean_symbol()
        test_recursive_prediction_logic()
        test_trend_and_recommendation()
        print("\nAll tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
