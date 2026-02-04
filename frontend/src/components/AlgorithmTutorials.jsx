import React, { useState } from "react";
import { FaBook, FaChartLine } from "react-icons/fa";
import "./AlgorithmTutorials.css";

const AlgorithmTutorials = ({ isOpen, onClose }) => {
  const [selectedAlgo, setSelectedAlgo] = useState("linear_regression");

  const CATEGORIES = {
    linear: "Linear & simple",
    ensemble: "Tree & ensemble",
    other: "Other methods",
  };

  const tutorials = {
    linear_regression: {
      name: "Linear Regression",
      category: "linear",
      tagline: "Fit a straight line to past prices and extend it into the future.",
      description: "A fundamental approach that models price as a linear function of time or other features. It finds the line that minimizes squared prediction errors (least squares) and assumes that trend continues.",
      howItWorks: [
        "Fits the best straight line through historical price (or return) data",
        "Formula: Price ≈ slope × time + intercept (or using multiple features)",
        "Minimizes sum of squared errors between actual and predicted values",
        "Forecast = extend the line for future dates"
      ],
      strengths: [
        "Very simple and interpretable: you see the trend rate",
        "Fast to train and predict; low computational cost",
        "Works well when the market has a clear, sustained trend",
        "Useful as a baseline to compare against more complex models"
      ],
      weaknesses: [
        "Cannot capture curves, cycles, or sudden regime changes",
        "Poor when volatility or trend strength changes over time",
        "Sensitive to outliers (e.g. a single crash can tilt the line)"
      ],
      useCase: "Best for stable, trending markets where price has moved in a roughly straight line over your chosen window.",
      example: "If a stock went from $90 to $110 over 20 days, linear regression might predict about $1/day gain and forecast $111 for the next day.",
      parameters: ["Feature set (e.g. time, lags)", "Whether to use returns vs levels"],
      proTip: "In this app, try it first on a symbol with a clear uptrend or downtrend; compare its MAE/RMSE with tree-based models to see when simplicity wins.",
    },
    elastic_net: {
      name: "Elastic Net",
      category: "linear",
      tagline: "Linear regression with built-in feature selection and stability for correlated inputs.",
      description: "Adds a penalty to the linear model that both shrinks coefficients (Ridge) and can set some to zero (Lasso). The mix helps when you have many correlated features, like multiple lagged returns.",
      howItWorks: [
        "Same as linear regression, but the loss includes penalty terms",
        "L1 (Lasso): encourages some coefficients to become exactly zero → feature selection",
        "L2 (Ridge): shrinks all coefficients → stable estimates when features are correlated",
        "Elastic Net combines both; you (or the app) choose the mix and strength"
      ],
      strengths: [
        "Handles many correlated inputs (e.g. 10 lagged returns) without blowing up",
        "You get a sparse model: only the most useful lags/features stay in",
        "More stable and interpretable than a plain linear model with many features"
      ],
      weaknesses: [
        "Still linear: cannot model complex non-linear relationships",
        "Sensitive to how features are scaled; tuning the penalty matters"
      ],
      useCase: "Best when you have many potential inputs (lags, indicators) and want a simple, interpretable linear forecast that automatically picks the most useful ones.",
      example: "With 20 lagged returns as features, Elastic Net might keep only 5 with non-zero coefficients, e.g. lags 1, 2, 5, 10, 20.",
      parameters: ["Regularization strength", "L1 vs L2 mix (alpha)"],
      proTip: "Use it in Future Prediction when you want to see which time lags the model considers important; compare with Linear Regression when you have many features.",
    },
    moving_average: {
      name: "Moving Average",
      category: "linear",
      tagline: "Smooth past prices and use the recent average (and trend) to forecast.",
      description: "No machine learning training—just average the last N prices (SMA) or use an exponentially weighted average (EMA). The forecast often follows the level or slope of that average.",
      howItWorks: [
        "SMA: average of the last N closing prices; EMA: weighted average with more weight on recent days",
        "The moving average smooths out noise and highlights the recent trend",
        "Forecast is typically the last MA value, or MA plus a small trend adjustment",
        "Only choice: window length N (and decay factor for EMA)"
      ],
      strengths: [
        "Extremely simple and fast; no training step",
        "Easy to explain and to overlay on charts",
        "Good baseline and works well in combination with other signals"
      ],
      weaknesses: [
        "Always lags: by the time the MA turns, the move has already happened",
        "Cannot capture non-linear behavior or regime shifts",
        "Window length is critical and somewhat arbitrary"
      ],
      useCase: "Best as a baseline or for smooth, steadily trending markets where “recent average price” is a reasonable guess for the near term.",
      example: "A 20-day SMA at $100 that has been rising $0.50/day might lead to a next-day forecast of $100.50.",
      parameters: ["Window size (e.g. 20 days)", "SMA vs EMA and decay"],
      proTip: "In Stock Analysis and Future Prediction, compare Moving Average with Linear Regression; MA is even simpler and often competitive in low-volatility periods.",
    },
    random_forest: {
      name: "Random Forest",
      category: "ensemble",
      tagline: "Many decision trees vote on the prediction; robust and good with non-linear patterns.",
      description: "Builds dozens or hundreds of trees, each on a random subset of data and features. Each tree votes (or averages) for the prediction; the ensemble reduces overfitting and handles non-linear relationships well.",
      howItWorks: [
        "Each tree is built on a random sample of rows and a random subset of features",
        "Trees ask yes/no questions (e.g. “Is 5-day return > 0?”) to split the data",
        "Prediction is the average (or majority) of all trees’ outputs",
        "Averaging many different trees smooths noise and reduces overfitting"
      ],
      strengths: [
        "Captures non-linear and interaction effects (e.g. “if volatility high and RSI > 70, often down”)",
        "Robust to outliers and missing values; rarely needs heavy feature engineering",
        "Can output feature importance to see which inputs matter most"
      ],
      weaknesses: [
        "Slower and uses more memory than a single tree or linear model",
        "Less interpretable than one simple tree or regression",
        "Can still overfit if trees are too deep or data is very noisy"
      ],
      useCase: "Excellent when you have multiple features (returns, volume, volatility, etc.) and expect non-linear or interactive effects.",
      example: "One tree might say “if 10-day return > 2% and volume > 1.5× average, predict +0.5%”; another might use different splits; the forest averages them.",
      parameters: ["Number of trees", "Max depth", "Min samples per leaf"],
      proTip: "Use alongside XGBoost and Gradient Boosting in Future Prediction; if Random Forest is close in accuracy, it’s often easier to explain and tune.",
    },
    xgboost: {
      name: "XGBoost (Extreme Gradient Boosting)",
      category: "ensemble",
      tagline: "Sequential trees that each correct the previous ones’ errors; often top accuracy.",
      description: "Builds trees one after another; each new tree is fit to the errors (residuals) of the current ensemble. Regularization and careful tuning help avoid overfitting while capturing complex patterns.",
      howItWorks: [
        "Start with a simple prediction (e.g. mean price). Compute errors.",
        "Fit a new tree to predict those errors (residuals), not the original target",
        "Add this tree to the ensemble with a small weight (learning rate); repeat",
        "Regularization (depth, min samples, L1/L2 on leaf weights) limits overfitting"
      ],
      strengths: [
        "Often achieves the best accuracy among tree-based models on tabular data",
        "Handles non-linear relationships and mixed feature types",
        "Efficient implementation; supports GPU and parallelization"
      ],
      weaknesses: [
        "Many hyperparameters (learning rate, depth, number of rounds); tuning takes time",
        "Easily overfits if not regularized or if trained too long",
        "Less interpretable than Random Forest (no simple “average of independent trees”)"
      ],
      useCase: "Ideal when you care most about prediction accuracy and have enough data to tune and validate; often the best single model in competitions and benchmarks.",
      example: "Tree 1 predicts +$1, but actual was +$2; tree 2 learns to add about $1 more; tree 3 corrects remaining errors; final prediction = sum of all tree outputs.",
      parameters: ["Learning rate", "Max depth", "Number of rounds", "L1/L2 regularization"],
      proTip: "In Compare algorithms, XGBoost often wins on MAE/RMSE; use it as your accuracy benchmark and compare others against it.",
    },
    gradient_boosting: {
      name: "Gradient Boosting",
      category: "ensemble",
      tagline: "Like XGBoost: trees added sequentially to correct errors, with flexible loss functions.",
      description: "Same idea as XGBoost: build trees one at a time, each targeting the current model’s errors. Classic gradient boosting uses gradient descent to choose how each tree is added; XGBoost is a highly optimized variant.",
      howItWorks: [
        "Initial prediction = constant (e.g. mean). Compute residuals.",
        "Fit a small tree to the residuals; add it to the model with a learning rate",
        "Update residuals and fit the next tree; repeat for many rounds",
        "Final prediction = initial + sum of (learning_rate × tree predictions)"
      ],
      strengths: [
        "Flexible: different loss functions for regression, classification, etc.",
        "Strong performance on structured data with proper tuning",
        "Handles mixed feature types and missing values well"
      ],
      weaknesses: [
        "Slower to train than Random Forest (trees are built sequentially)",
        "Learning rate and number of trees need tuning to avoid overfitting",
        "More implementation details to get right than Random Forest"
      ],
      useCase: "Good when you want XGBoost-style accuracy with a different implementation or loss; often comparable to XGBoost with similar hyperparameters.",
      example: "Similar to XGBoost: first tree gets most of the trend, later trees refine details; early stopping can prevent overfitting.",
      parameters: ["Learning rate", "Number of trees", "Max depth", "Min samples per leaf"],
      proTip: "Compare Gradient Boosting and XGBoost in the same run; they often give similar results, with XGBoost sometimes faster.",
    },
    svm: {
      name: "Support Vector Machine (SVM)",
      category: "other",
      tagline: "Finds a boundary that best separates different outcomes; powerful in high dimensions.",
      description: "In regression mode (SVR), the model finds a tube around the data that minimizes error while maximizing margin. The “kernel trick” allows non-linear boundaries without explicitly transforming features.",
      howItWorks: [
        "Maps inputs into a (possibly high-dimensional) space via a kernel function",
        "Finds a hyperplane (or tube for regression) that fits the data with a margin",
        "Only a subset of points (“support vectors”) define the solution",
        "Prediction depends on which side of the boundary (or distance to the tube) new points fall"
      ],
      strengths: [
        "Works well in high dimensions and with limited data when the kernel fits the structure",
        "Flexible kernels (RBF, polynomial) can capture non-linear patterns",
        "Strong theoretical foundation and generalization bounds"
      ],
      weaknesses: [
        "Training can be slow on large datasets (e.g. long history)",
        "Sensitive to kernel and regularization (C, gamma) choices",
        "Less common for time-series forecasting than trees or linear models"
      ],
      useCase: "Best when you have a moderate number of observations and believe a clear boundary or smooth function separates good vs bad forecasts.",
      example: "In 2D: draw a curve that best separates “next-day up” from “next-day down” based on today’s return and volatility; prediction = which side new points fall on.",
      parameters: ["Kernel (e.g. RBF, linear)", "C (regularization)", "Gamma (kernel width)"],
      proTip: "Try SVM when you have a smaller date range or fewer features; it can compete with trees when data is clean and not huge.",
    },
    knn: {
      name: "K-Nearest Neighbors (KNN)",
      category: "other",
      tagline: "Find the k most similar past days and predict from their outcomes.",
      description: "For each forecast date, find the k historical points closest in feature space (e.g. recent returns, volume). Predict the average (or median) of their next-day outcomes. No explicit training—just store the data.",
      howItWorks: [
        "Define features for each day (e.g. 5-day return, volume ratio, volatility)",
        "For the day to forecast, compute distance to every historical day",
        "Select the k smallest distances (nearest neighbors)",
        "Prediction = average of those k days’ next-day returns (or prices)"
      ],
      strengths: [
        "No training step; simple and intuitive (“find similar past days”)",
        "Can capture local, non-linear structure without assuming a global model",
        "Works with any distance metric; easy to try different feature sets"
      ],
      weaknesses: [
        "Prediction is slow when you have lots of history (must compare to all points)",
        "Sensitive to scale of features and to irrelevant features",
        "Curse of dimensionality: needs many samples when feature count is high"
      ],
      useCase: "Good for exploratory analysis and when you believe “similar past situations lead to similar outcomes” (e.g. similar volatility and momentum).",
      example: "Today’s 5-day return and volatility are (2%, 0.8). The 3 nearest past days had next-day returns +0.5%, −0.2%, +0.8% → predict +0.37%.",
      parameters: ["k (number of neighbors)", "Distance metric", "Feature set and scaling"],
      proTip: "Use a smaller k for more responsive, noisier predictions; larger k for smoother, more stable forecasts. Compare with Moving Average for a different kind of “recent history” baseline.",
    },
  };

  const algo = tutorials[selectedAlgo];
  const orderByCategory = ["linear", "ensemble", "other"];
  const entriesByCategory = orderByCategory.map((cat) => ({
    category: cat,
    label: CATEGORIES[cat],
    algorithms: Object.entries(tutorials).filter(([, d]) => d.category === cat),
  }));

  if (!isOpen) return null;

  return (
    <div className="algorithm-tutorials-overlay" onClick={onClose}>
      <div className="algorithm-tutorials-panel" onClick={(e) => e.stopPropagation()}>
        <div className="tutorials-header d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-2">
            <FaBook className="text-primary" size={24} />
            <h2 className="mb-0">Algorithm Tutorials</h2>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close" />
        </div>

        <div className="tutorials-container">
          <div className="tutorials-sidebar">
            <p className="tutorials-sidebar-intro px-3 small text-muted mb-3">
              Learn how each algorithm works and when to use it in Stock Analysis and Future Prediction.
            </p>
            {entriesByCategory.map(({ category, label, algorithms }) => (
              <div key={category} className="tutorials-sidebar-group">
                <h6 className="tutorials-sidebar-category">{label}</h6>
                {algorithms.map(([key, data]) => (
                  <button
                    key={key}
                    type="button"
                    className={`tutorial-btn w-100 text-start px-3 py-2 border-0 ${selectedAlgo === key ? "active" : ""}`}
                    onClick={() => setSelectedAlgo(key)}
                  >
                    <FaChartLine className="me-2" />
                    {data.name}
                  </button>
                ))}
              </div>
            ))}
          </div>

          <div className="tutorials-content">
            {algo && (
              <>
                <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
                  <span className="tutorial-category-badge">{CATEGORIES[algo.category]}</span>
                </div>
                <h3 className="mb-1">{algo.name}</h3>
                {algo.tagline && <p className="tutorial-tagline text-muted mb-3">{algo.tagline}</p>}
                <p className="mb-4">{algo.description}</p>

                <h5 className="mt-4 mb-3">How It Works</h5>
                <ul className="list-unstyled mb-4">
                  {algo.howItWorks.map((step, idx) => (
                    <li key={idx} className="d-flex gap-2 mb-2">
                      <span className="badge bg-primary text-white mt-1 flex-shrink-0">{idx + 1}</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>

                {algo.parameters && algo.parameters.length > 0 && (
                  <>
                    <h5 className="mb-2">Key parameters</h5>
                    <ul className="tutorial-params list-unstyled mb-4">
                      {algo.parameters.map((param, idx) => (
                        <li key={idx} className="mb-1">{param}</li>
                      ))}
                    </ul>
                  </>
                )}

                <div className="row mb-4">
                  <div className="col-md-6">
                    <h5 className="mb-3 text-success">Strengths</h5>
                    <ul className="list-unstyled">
                      {algo.strengths.map((strength, idx) => (
                        <li key={idx} className="mb-2 text-success d-flex gap-2">
                          <span className="flex-shrink-0">✓</span>
                          <span>{strength}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="col-md-6">
                    <h5 className="mb-3 text-danger">Weaknesses</h5>
                    <ul className="list-unstyled">
                      {algo.weaknesses.map((weakness, idx) => (
                        <li key={idx} className="mb-2 text-danger d-flex gap-2">
                          <span className="flex-shrink-0">✗</span>
                          <span>{weakness}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <h5 className="mb-2">Use case</h5>
                <p className="tutorial-use-case bg-light p-3 rounded mb-4">{algo.useCase}</p>

                <h5 className="mb-2">Example</h5>
                <p className="tutorial-example bg-light p-3 rounded mb-4">{algo.example}</p>

                {algo.proTip && (
                  <div className="tutorial-pro-tip p-3 rounded">
                    <strong className="d-block mb-1">In this app</strong>
                    <span>{algo.proTip}</span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlgorithmTutorials;
