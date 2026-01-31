import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { FaArrowUp, FaArrowDown, FaCalendarAlt, FaHistory } from "react-icons/fa";
import "./FuturePrediction.css";

const FuturePrediction = () => {
  const [symbol, setSymbol] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [predictionLength, setPredictionLength] = useState(7);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [watchlist, setWatchlist] = useState([]);

  const availableAlgorithms = [
    { key: "linear_regression", label: "Linear Regression" },
    { key: "random_forest", label: "Random Forest" },
    { key: "xgboost", label: "XGBoost" },
    { key: "gradient_boosting", label: "Gradient Boosting" },
    { key: "svm", label: "SVM" },
    { key: "knn", label: "KNN" },
  ];
  const [selectedAlgorithms, setSelectedAlgorithms] = useState([
    "linear_regression",
    "random_forest",
    "xgboost",
  ]);

  useEffect(() => {
    const today = new Date();
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(today.getMonth() - 6);

    setEndDate(today.toISOString().split("T")[0]);
    setStartDate(sixMonthsAgo.toISOString().split("T")[0]);

    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const response = await axios.get("http://localhost:5000/api/watchlist");
      const list = response.data.watchlist || [];
      setWatchlist(list);
      if (list.length > 0) setSymbol(list[0].symbol);
    } catch (err) {
      console.error("Failed to fetch watchlist", err);
    }
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post("http://localhost:5000/api/predict-future", {
        symbol,
        startDate,
        endDate,
        prediction_length: predictionLength,
        algorithms: selectedAlgorithms.length > 0 ? selectedAlgorithms : ["linear_regression", "random_forest", "xgboost"],
      });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to get predictions. Please try a different symbol or date range.');
    } finally {
      setLoading(false);
    }
  };

  const prepareChartData = () => {
    if (!result) return [];

    const historicalData = result.historical.dates.map((date, i) => ({
      date: date.slice(0, 10),
      historical: result.historical.prices[i],
    }));

    const futureData = result.dates.map((date, i) => {
      const item = {
        date: date.slice(0, 10),
        actualCompare: result.actual_future ? result.actual_future[i] : null,
      };
      const algos = (selectedAlgorithms && selectedAlgorithms.length > 0) ? selectedAlgorithms : Object.keys(result.predictions);
      algos.forEach((algo) => {
        if (result.predictions[algo]) item[algo] = result.predictions[algo][i];
      });
      const prices = algos.filter((a) => result.predictions[a]).map((a) => result.predictions[a][i]);
      item.consensus = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : null;
      return item;
    });

    return [...historicalData, ...futureData];
  };

  const chartData = prepareChartData();

  return (
    <div className="future-prediction">
      <h1 className="mb-4">Future Prediction</h1>
      <p className="text-muted mb-4">Project future market trends using ensemble models and majority voting consensus.</p>

      <div className="card card-body mb-4 shadow-sm border-0 bg-light">
        <form onSubmit={handlePredict} className="prediction-form row g-3">
          <div className="col-md-4">
            <label className="form-label fw-bold">Company</label>
            <select className="form-select" value={symbol} onChange={(e) => setSymbol(e.target.value)} required>
              <option value="">Select company…</option>
              {watchlist.map(item => (
                <option key={item.id} value={item.symbol}>{item.symbol}{item.company_name && item.company_name !== item.symbol ? ` (${item.company_name})` : ''}</option>
              ))}
            </select>
          </div>

          <div className="col-md-2">
            <label className="form-label fw-bold">Start Date</label>
            <input type="date" className="form-control" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>

          <div className="col-md-2">
            <label className="form-label fw-bold">End Date</label>
            <input type="date" className="form-control" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>

          <div className="col-md-2">
            <label className="form-label fw-bold">Days Ahead</label>
            <input type="number" className="form-control" min="1" max="30" value={predictionLength} onChange={(e) => setPredictionLength(e.target.value)} />
          </div>

          <div className="col-md-2 d-flex align-items-end">
            <div style={{ width: '100%' }}>
              <label className="form-label fw-bold">Algorithms</label>
              <select multiple size={3} className="form-select algos-select mb-1" value={selectedAlgorithms} onChange={(e) => {
                const options = Array.from(e.target.options);
                const vals = options.filter(o => o.selected).map(o => o.value);
                setSelectedAlgorithms(vals);
              }}>
                {availableAlgorithms.map(a => (<option key={a.key} value={a.key}>{a.label}</option>))}
              </select>
              <button type="submit" className="btn btn-primary w-100 fw-bold mt-1 forecast-btn" disabled={loading || !symbol}>{loading ? 'Analyzing…' : 'Forecast'}</button>
            </div>
          </div>
        </form>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {result && (
        <div className="row">
          <div className="col-12 mb-4">
            <div className={`card shadow-sm border-0 text-white ${result.recommendation.includes('Buy') ? 'bg-success' : result.recommendation.includes('Sell') ? 'bg-danger' : 'bg-secondary'}`}>
              <div className="card-body d-flex justify-content-between align-items-center py-4">
                <div>
                  <h4 className="mb-1 fw-bold">Ensemble Majority Decision</h4>
                  <p className="mb-0 opacity-75">Based on a majority vote of {(selectedAlgorithms && selectedAlgorithms.length > 0) ? selectedAlgorithms.length : Object.keys(result.predictions).length} independent models</p>
                </div>
                <div className="text-end">
                  <h2 className="mb-0 fw-bold text-uppercase">{result.recommendation}</h2>
                  <div className="small fw-bold opacity-75">OVERALL MARKET TREND</div>
                </div>
              </div>
            </div>
          </div>

          <div className="col-lg-8 mb-4">
            <div className="card card-body h-100 shadow-sm border-0">
              <h5 className="card-title mb-4 fw-bold text-dark"><FaHistory className="me-2 text-primary" /> Price Forecast</h5>
              <div style={{ width: '100%', height: 400 }}>
                <ResponsiveContainer>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} />
                    <YAxis domain={["auto", "auto"]} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                    <Legend />
                    <Line type="monotone" dataKey="historical" stroke="#0d6efd" strokeWidth={3} name="Historical" dot={false} />
                    <Line type="monotone" dataKey="actualCompare" stroke="#212529" strokeWidth={3} name="Actual (Ground Truth)" strokeDasharray="3 3" dot={true} />
                    <Line type="monotone" dataKey="consensus" stroke="#ffc107" strokeWidth={3} strokeDasharray="5 5" name="Ensemble Consensus" />
                    {((selectedAlgorithms && selectedAlgorithms.length > 0) ? selectedAlgorithms : Object.keys(result.predictions)).map((algo) => {
                      const strokeMap = {
                        linear_regression: '#198754',
                        random_forest: '#fd7e14',
                        xgboost: '#6f42c1',
                        gradient_boosting: '#0dcaf0',
                        svm: '#6c757d',
                        knn: '#6610f2'
                      };
                      const nameMap = {
                        linear_regression: 'Lin Reg',
                        random_forest: 'Rand Forest',
                        xgboost: 'XGBoost',
                        gradient_boosting: 'Grad Boost',
                        svm: 'SVM',
                        knn: 'KNN'
                      };
                      return (<Line key={algo} type="monotone" dataKey={algo} stroke={strokeMap[algo] || '#8884d8'} strokeWidth={1} dot={false} name={nameMap[algo] || algo} />);
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="col-lg-4 mb-4">
            <div className="card h-100 shadow-sm border-0">
              <div className="card-header bg-white border-bottom-0 pt-4">
                <h5 className="mb-0 fw-bold text-dark"><FaCalendarAlt className="me-2 text-primary" /> Consensus Trend</h5>
                <p className="small text-muted mb-0">Daily prediction majority vote</p>
              </div>
              <div className="card-body px-0 pt-2">
                <div className="list-group list-group-flush">
                  {result.voting.map((vote, idx) => (
                    <div key={idx} className="list-group-item d-flex justify-content-between align-items-center border-0 px-4 py-3">
                      <div>
                        <div className="fw-bold mb-1">{vote.date}</div>
                        <div className={`badge rounded-pill ${vote.trend === 'Up' ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'}`} style={{ fontSize: '0.8rem' }}>
                          {vote.trend === 'Up' ? <FaArrowUp className="me-1" /> : <FaArrowDown className="me-1" />} {vote.trend}
                        </div>
                      </div>
                      <div className="text-end">
                        <div className="fw-bold" style={{ color: '#0d6efd' }}>{vote.confidence}%</div>
                        <div className="small text-muted">Confidence</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FuturePrediction;
    const today = new Date();
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(today.getMonth() - 6);

    setEndDate(today.toISOString().split("T")[0]);
    setStartDate(sixMonthsAgo.toISOString().split("T")[0]);

    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const response = await axios.get("http://localhost:5000/api/watchlist");
      const list = response.data.watchlist || [];
      setWatchlist(list);
      if (list.length > 0) {
        setSymbol(list[0].symbol);
      }
    } catch (err) {
      console.error("Failed to fetch watchlist", err);
    }
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(
        "http://localhost:5000/api/predict-future",
        {
          symbol,
          startDate,
          endDate,
          prediction_length: predictionLength,
          algorithms:
            selectedAlgorithms.length > 0
              ? selectedAlgorithms
              : ["linear_regression", "random_forest", "xgboost"],
        },
      );
      setResult(response.data);
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Failed to get predictions. Please try a different symbol or date range.",
      );
    } finally {
      setLoading(false);
    }
  };

  const prepareChartData = () => {
    if (!result) return [];

    const historicalData = result.historical.dates.map((date, i) => ({
      date: date.slice(0, 10),
      historical: result.historical.prices[i],
    }));

    const futureData = result.dates.map((date, i) => {
      const item = {
        date: date.slice(0, 10),
        actualCompare: result.actual_future ? result.actual_future[i] : null,
      };
      const algos =
        selectedAlgorithms && selectedAlgorithms.length > 0
          ? selectedAlgorithms
          : Object.keys(result.predictions);
      algos.forEach((algo) => {
        if (result.predictions[algo]) item[algo] = result.predictions[algo][i];
      });
      const prices = algos
        .filter((a) => result.predictions[a])
        .map((a) => result.predictions[a][i]);
      item.consensus = prices.reduce((a, b) => a + b, 0) / prices.length;
      return item;
    });

    return [...historicalData, ...futureData];
  };

  const chartData = prepareChartData();

  return (
    <div className="future-prediction">
      <h1 className="mb-4">Future Prediction</h1>
      <p className="text-muted mb-4">
        Project future market trends using ensemble models and majority voting
        consensus.
      </p>

      <div className="card card-body mb-4 shadow-sm border-0 bg-light">
        <form onSubmit={handlePredict} className="prediction-form row g-3">
          <div className="col-md-4">
            <label className="form-label fw-bold">Company</label>
            <select
              className="form-select"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              required
            >
              <option value="">Select company…</option>
              {watchlist.map((item) => (
                <option key={item.id} value={item.symbol}>
                  {item.symbol}{" "}
                  {item.company_name && item.company_name !== item.symbol
                    ? `(${item.company_name})`
                    : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label fw-bold">Start Date</label>
            <input
              type="date"
              className="form-control"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label fw-bold">End Date</label>
            <input
              type="date"
              className="form-control"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label fw-bold">Days Ahead</label>
            <input
              type="number"
              className="form-control"
              min="1"
              max="30"
              value={predictionLength}
              onChange={(e) => setPredictionLength(e.target.value)}
            />
          </div>
          <div className="col-md-2 d-flex align-items-end">
            <div style={{ width: "100%" }}>
              <label className="form-label fw-bold">Algorithms</label>
              <select
                multiple
                size={4}
                className="form-select mb-2"
                value={selectedAlgorithms}
                onChange={(e) => {
                  const options = Array.from(e.target.options);
                  const vals = options
                    .filter((o) => o.selected)
                    .map((o) => o.value);
                  setSelectedAlgorithms(vals);
                }}
              >
                {availableAlgorithms.map((a) => (
                  <option key={a.key} value={a.key}>
                    {a.label}
                  </option>
                ))}
              </select>
              <button
                type="submit"
                className="btn btn-primary w-100 fw-bold"
                disabled={loading || !symbol}
              >
                {loading ? "Analyzing…" : "Forecast"}
              </button>
            </div>
          </div>
        </form>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {result && (
        <div className="row">
          <div className="col-12 mb-4">
            <div
              className={`card shadow-sm border-0 text-white ${
                result.recommendation.includes("Buy")
                  ? "bg-success"
                  : result.recommendation.includes("Sell")
                    ? "bg-danger"
                    : "bg-secondary"
              }`}
            >
              <div className="card-body d-flex justify-content-between align-items-center py-4">
                <div>
                  <h4 className="mb-1 fw-bold">Ensemble Majority Decision</h4>
                  <p className="mb-0 opacity-75">
                    Based on a majority vote of{" "}
                    {selectedAlgorithms && selectedAlgorithms.length > 0
                      ? selectedAlgorithms.length
                      : Object.keys(result.predictions).length}{" "}
                    independent models
                  </p>
                </div>
                <div className="text-end">
                  <h2 className="mb-0 fw-bold text-uppercase">
                    {result.recommendation}
                  </h2>
                  <div className="small fw-bold opacity-75">
                    OVERALL MARKET TREND
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="col-lg-8 mb-4">
            <div className="card card-body h-100 shadow-sm border-0">
              <h5 className="card-title mb-4 fw-bold text-dark">
                <FaHistory className="me-2 text-primary" /> Price Forecast
              </h5>
              <div style={{ width: "100%", height: 400 }}>
                <ResponsiveContainer>
                  <LineChart data={chartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                      stroke="#eee"
                    />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} />
                    <YAxis
                      domain={["auto", "auto"]}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "none",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="historical"
                      stroke="#0d6efd"
                      strokeWidth={3}
                      name="Historical"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="actualCompare"
                      stroke="#212529"
                      strokeWidth={3}
                      name="Actual (Ground Truth)"
                      strokeDasharray="3 3"
                      dot={true}
                    />
                    <Line
                      type="monotone"
                      dataKey="consensus"
                      stroke="#ffc107"
                      strokeWidth={3}
                      strokeDasharray="5 5"
                      name="Ensemble Consensus"
                    />
                    {(selectedAlgorithms && selectedAlgorithms.length > 0
                      ? selectedAlgorithms
                      : Object.keys(result.predictions)
                    ).map((algo) => {
                      const strokeMap = {
                        linear_regression: "#198754",
                        random_forest: "#fd7e14",
                        xgboost: "#6f42c1",
                        gradient_boosting: "#0dcaf0",
                        svm: "#6c757d",
                        knn: "#6610f2",
                      };
                      const nameMap = {
                        linear_regression: "Lin Reg",
                        random_forest: "Rand Forest",
                        xgboost: "XGBoost",
                        gradient_boosting: "Grad Boost",
                        svm: "SVM",
                        knn: "KNN",
                      };
                      return (
                        <Line
                          key={algo}
                          type="monotone"
                          dataKey={algo}
                          stroke={strokeMap[algo] || "#8884d8"}
                          strokeWidth={1}
                          dot={false}
                          name={nameMap[algo] || algo}
                        />
                      );
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="col-lg-4 mb-4">
            <div className="card h-100 shadow-sm border-0">
              <div className="card-header bg-white border-bottom-0 pt-4">
                <h5 className="mb-0 fw-bold text-dark">
                  <FaCalendarAlt className="me-2 text-primary" /> Consensus
                  Trend
                </h5>
                <p className="small text-muted mb-0">
                  Daily prediction majority vote
                </p>
              </div>
              <div className="card-body px-0 pt-2">
                <div className="list-group list-group-flush">
                  {result.voting.map((vote, idx) => (
                    <div
                      key={idx}
                      className="list-group-item d-flex justify-content-between align-items-center border-0 px-4 py-3"
                    >
                      <div>
                        <div className="fw-bold mb-1">{vote.date}</div>
                        <div
                          className={`badge rounded-pill ${vote.trend === "Up" ? "bg-success-subtle text-success" : "bg-danger-subtle text-danger"}`}
                          style={{ fontSize: "0.8rem" }}
                        >
                          {vote.trend === "Up" ? (
                            <FaArrowUp className="me-1" />
                          ) : (
                            <FaArrowDown className="me-1" />
                          )}{" "}
                          {vote.trend}
                        </div>
                      </div>
                      <div className="text-end">
                        <div className="fw-bold" style={{ color: "#0d6efd" }}>
                          {vote.confidence}%
                        </div>
                        <div className="small text-muted">Confidence</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FuturePrediction;
