import React, { useState } from "react";
import { FaBook, FaTimes, FaChartLine } from "react-icons/fa";
import "./AlgorithmTutorials.css";

const AlgorithmTutorials = ({ isOpen, onClose }) => {
  const [selectedAlgo, setSelectedAlgo] = useState("linear_regression");

  const tutorials = {
    linear_regression: {
      name: "Linear Regression",
      description: "A fundamental machine learning algorithm that models the linear relationship between input features and output.",
      howItWorks: [
        "Finds the best-fit straight line through historical price data",
        "Equation: Price = m × Time + b (where m is slope, b is intercept)",
        "Uses least squares method to minimize prediction errors",
        "Assumes linear trend continues into the future"
      ],
      strengths: [
        "Simple and interpretable",
        "Fast to train and predict",
        "Works well for data with linear trends",
        "Low computational cost"
      ],
      weaknesses: [
        "Cannot capture non-linear patterns",
        "Poor performance on complex market dynamics",
        "Assumes constant rate of change",
        "Sensitive to outliers"
      ],
      useCase: "Best for stable, trending markets with consistent patterns over time",
      example: "If stock price increased $2/day for 100 days, it would predict $2/day increase continuing"
    },
    random_forest: {
      name: "Random Forest",
      description: "An ensemble method that combines multiple decision trees to make more robust predictions.",
      howItWorks: [
        "Creates many random decision trees, each trained on random subsets of data",
        "Each tree learns patterns by asking yes/no questions (e.g., 'Is price > $100?')",
        "Combines predictions from all trees using majority voting or averaging",
        "Reduces overfitting by averaging results across diverse trees"
      ],
      strengths: [
        "Captures non-linear relationships",
        "Robust to outliers and noise",
        "Handles multiple features well",
        "Provides feature importance rankings"
      ],
      weaknesses: [
        "Less interpretable than single models",
        "Slower to train with many trees",
        "May require more memory",
        "Can overfit with shallow trees"
      ],
      useCase: "Excellent for complex, non-linear market patterns with multiple influencing factors",
      example: "Learns rules like 'If volatility high AND RSI > 70, price drops', combining many such patterns"
    },
    xgboost: {
      name: "XGBoost (Extreme Gradient Boosting)",
      description: "A powerful ensemble technique that builds trees sequentially, each correcting errors from previous trees.",
      howItWorks: [
        "Trains first tree on the data and calculates residual errors",
        "Each subsequent tree focuses on correcting previous errors",
        "Weights samples that were mispredicted more heavily",
        "Final prediction is sum of all tree predictions with shrinkage (regularization)"
      ],
      strengths: [
        "Often best accuracy among tree-based models",
        "Handles both linear and non-linear patterns",
        "Built-in regularization prevents overfitting",
        "Fast computation with GPU support"
      ],
      weaknesses: [
        "Hyperparameters require careful tuning",
        "Risk of overfitting if not properly regularized",
        "Less interpretable than simpler models",
        "More complex to understand and debug"
      ],
      useCase: "Ideal for high-accuracy predictions on complex financial data with many variables",
      example: "First tree predicts, makes errors; second tree learns from errors; third refines further, etc."
    },
    gradient_boosting: {
      name: "Gradient Boosting",
      description: "Similar to XGBoost but uses gradient descent optimization for building sequential trees.",
      howItWorks: [
        "Starts with initial simple prediction (mean price)",
        "Calculates prediction errors (residuals)",
        "Builds new tree to predict residuals, not original target",
        "Multiplies tree predictions by learning rate and adds to previous prediction",
        "Repeats process to progressively improve predictions"
      ],
      strengths: [
        "Flexible loss functions for different objectives",
        "Excellent generalization with proper tuning",
        "Handles mixed feature types well",
        "Strong performance on structured data"
      ],
      weaknesses: [
        "Prone to overfitting if learning rate too high",
        "Requires careful parameter tuning",
        "Slower training than Random Forest",
        "Sequential nature prevents parallelization"
      ],
      useCase: "Good for datasets where capturing gradual improvements in accuracy is important",
      example: "Predicts $105, realizes it should be $108; next model predicts $3 more; continues refining"
    },
    svm: {
      name: "Support Vector Machine (SVM)",
      description: "Finds optimal boundaries to separate data points, then uses support vectors for predictions.",
      howItWorks: [
        "Maps data into higher-dimensional space if needed (kernel trick)",
        "Finds hyperplane that maximally separates different price trends",
        "Uses support vectors (critical data points) to define decision boundaries",
        "Predicts price movement based on which side of hyperplane data falls"
      ],
      strengths: [
        "Powerful for high-dimensional data",
        "Works well with small to medium datasets",
        "Versatile kernel functions for different patterns",
        "Good generalization with proper kernel choice"
      ],
      weaknesses: [
        "Slower training on large datasets",
        "Difficult hyperparameter tuning (kernel, C, gamma)",
        "Less interpretable predictions",
        "May struggle with noisy financial data"
      ],
      useCase: "Best for pattern recognition in cleaned, structured historical data",
      example: "Draws a boundary line between days with price increases and decreases"
    },
    knn: {
      name: "K-Nearest Neighbors (KNN)",
      description: "A simple algorithm that classifies/predicts based on the k nearest historical data points.",
      howItWorks: [
        "For a new date, finds k most similar historical dates (by features like volatility, momentum)",
        "Looks at actual price movements of those k neighbors",
        "Predicts average or majority result from the k neighbors",
        "Distance metric (usually Euclidean) determines 'nearest'"
      ],
      strengths: [
        "Very simple to understand and implement",
        "No training phase (lazy learning)",
        "Can capture complex patterns in local neighborhoods",
        "Works with any distance metric"
      ],
      weaknesses: [
        "Slow prediction time (must compute distance to all training data)",
        "Sensitive to feature scaling",
        "Performs poorly with high-dimensional data",
        "Sensitive to noise and outliers"
      ],
      useCase: "Good for exploratory analysis and when similar historical patterns are most relevant",
      example: "If today looks like 3 past days where price rose 2%, predicts 2% rise"
    }
  };

  const algo = tutorials[selectedAlgo];

  if (!isOpen) return null;

  return (
    <div className="algorithm-tutorials-overlay" onClick={onClose}>
      <div className="algorithm-tutorials-panel" onClick={(e) => e.stopPropagation()}>
        <div className="tutorials-header d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-2">
            <FaBook className="text-primary" size={24} />
            <h2 className="mb-0">Algorithm Tutorials</h2>
          </div>
          <button className="btn-close" onClick={onClose} />
        </div>

        <div className="tutorials-container">
          <div className="tutorials-sidebar">
            <h6 className="text-muted mb-3 px-3">SELECT ALGORITHM</h6>
            {Object.entries(tutorials).map(([key, data]) => (
              <button
                key={key}
                className={`tutorial-btn w-100 text-start px-3 py-2 border-0 ${selectedAlgo === key ? "active" : ""}`}
                onClick={() => setSelectedAlgo(key)}
              >
                <FaChartLine className="me-2" />
                {data.name}
              </button>
            ))}
          </div>

          <div className="tutorials-content">
            {algo && (
              <>
                <h3 className="mb-2">{algo.name}</h3>
                <p className="text-muted mb-4">{algo.description}</p>

                <h5 className="mt-4 mb-3">How It Works</h5>
                <ul className="list-unstyled mb-4">
                  {algo.howItWorks.map((step, idx) => (
                    <li key={idx} className="d-flex gap-2 mb-2">
                      <span className="badge bg-primary text-white mt-1">{idx + 1}</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>

                <div className="row mb-4">
                  <div className="col-md-6">
                    <h5 className="mb-3 text-success">Strengths ✓</h5>
                    <ul className="list-unstyled">
                      {algo.strengths.map((strength, idx) => (
                        <li key={idx} className="mb-2 text-success">
                          <span className="me-2">✓</span>
                          {strength}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="col-md-6">
                    <h5 className="mb-3 text-danger">Weaknesses ✗</h5>
                    <ul className="list-unstyled">
                      {algo.weaknesses.map((weakness, idx) => (
                        <li key={idx} className="mb-2 text-danger">
                          <span className="me-2">✗</span>
                          {weakness}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <h5 className="mb-2">Use Case</h5>
                <p className="bg-light p-3 rounded mb-4">{algo.useCase}</p>

                <h5 className="mb-2">Example</h5>
                <p className="bg-light p-3 rounded">{algo.example}</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlgorithmTutorials;
