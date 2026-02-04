# Algorithm registry: name -> run_algorithm(data_config, csv_path) -> result dict
from algorithms import (
    markov_chains,
    linear_regression,
    arima,
    random_forest,
    xgboost_algo,
    svm_algo,
    knn_algo,
    gradient_boosting,
    moving_average,
    elastic_net,
    lstm,
)

ALGORITHMS = {
    "markov_chains": ("Markov Chains", markov_chains.run_algorithm),
    "linear_regression": ("Linear Regression", linear_regression.run_algorithm),
    "arima": ("ARIMA", arima.run_algorithm),
    "random_forest": ("Random Forest", random_forest.run_algorithm),
    "xgboost": ("XGBoost", xgboost_algo.run_algorithm),
    "svm": ("Support Vector Machine", svm_algo.run_algorithm),
    "knn": ("K-Nearest Neighbors", knn_algo.run_algorithm),
    "gradient_boosting": ("Gradient Boosting", gradient_boosting.run_algorithm),
    "moving_average": ("Moving Average", moving_average.run_algorithm),
    "elastic_net": ("Elastic Net", elastic_net.run_algorithm),
    "lstm": ("LSTM", lstm.run_algorithm),
}
