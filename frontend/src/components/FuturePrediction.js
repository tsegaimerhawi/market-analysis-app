import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { FaArrowUp, FaArrowDown, FaRobot, FaCalendarAlt, FaHistory } from 'react-icons/fa';
import './FuturePrediction.css';

const FuturePrediction = () => {
    const [symbol, setSymbol] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [predictionLength, setPredictionLength] = useState(7);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [watchlist, setWatchlist] = useState([]);

    useEffect(() => {
        fetchWatchlist();
    }, []);

    const fetchWatchlist = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/watchlist');
            setWatchlist(response.data.watchlist || []);
            if (response.data.watchlist?.length > 0) {
                setSymbol(response.data.watchlist[0].symbol);
            }
        } catch (err) {
            console.error('Failed to fetch watchlist', err);
        }
    };

    const handlePredict = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const response = await axios.post('http://localhost:5000/api/predict-future', {
                symbol,
                startDate,
                endDate,
                prediction_length: predictionLength,
                algorithms: JSON.stringify(["linear_regression", "random_forest", "xgboost"])
            });
            setResult(response.data);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to get predictions');
        } finally {
            setLoading(false);
        }
    };

    const prepareChartData = () => {
        if (!result) return [];

        const historicalData = result.historical.dates.map((date, i) => ({
            date,
            price: result.historical.prices[i],
            type: 'Historical'
        }));

        const futureData = result.dates.map((date, i) => {
            const item = { date, type: 'Predicted' };
            Object.keys(result.predictions).forEach(algo => {
                item[algo] = result.predictions[algo][i];
            });
            // Add a consensus price (average of all models)
            const prices = Object.values(result.predictions).map(p => p[i]);
            item.consensus = prices.reduce((a, b) => a + b, 0) / prices.length;
            return item;
        });

        // Merge: the last historical point should connect to future points
        const lastHistorical = historicalData[historicalData.length - 1];
        const connectedFutureData = futureData.map(d => ({ ...d }));

        // Add historical price to the first future entry for connection if needed
        // But Recharts handles gaps if we just provide the data points.

        return [...historicalData, ...connectedFutureData];
    };

    const chartData = prepareChartData();

    return (
        <div className="future-prediction-container">
            <div className="prediction-header">
                <h1><FaRobot /> Future Market Prediction</h1>
                <p>Predict stock trends using ensemble models and majority voting consensus.</p>
            </div>

            <div className="prediction-controls card">
                <form onSubmit={handlePredict} className="prediction-form">
                    <div className="form-group">
                        <label>Select Company</label>
                        <select value={symbol} onChange={(e) => setSymbol(e.target.value)} required>
                            <option value="">-- Choose Ticker --</option>
                            {watchlist.map(item => (
                                <option key={item.id} value={item.symbol}>{item.symbol} - {item.company_name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label>Start Date (Optional)</label>
                        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label>End Date (Optional)</label>
                        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label>Prediction Length (Days)</label>
                        <input
                            type="number"
                            min="1"
                            max="30"
                            value={predictionLength}
                            onChange={(e) => setPredictionLength(e.target.value)}
                        />
                    </div>
                    <button type="submit" className="predict-btn" disabled={loading}>
                        {loading ? 'Analyzing...' : 'Run Prediction'}
                    </button>
                </form>
            </div>

            {error && <div className="error-message">{error}</div>}

            {result && (
                <div className="prediction-results">
                    <div className="results-grid">
                        <div className="chart-section card">
                            <h3><FaHistory /> Price Forecast</h3>
                            <div style={{ width: '100%', height: 400 }}>
                                <ResponsiveContainer>
                                    <LineChart data={chartData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                                        <XAxis dataKey="date" stroke="#ccc" />
                                        <YAxis stroke="#ccc" />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#222', border: '1px solid #444', color: '#fff' }}
                                            itemStyle={{ color: '#fff' }}
                                        />
                                        <Legend />
                                        <Line type="monotone" dataKey="price" stroke="#3498db" strokeWidth={3} name="Historical" dot={false} />
                                        <Line type="monotone" dataKey="consensus" stroke="#f1c40f" strokeWidth={3} strokeDasharray="5 5" name="Consensus Prediction" />
                                        <Line type="monotone" dataKey="linear_regression" stroke="#2ecc71" strokeWidth={1} dot={false} name="Linear Regression" />
                                        <Line type="monotone" dataKey="random_forest" stroke="#e67e22" strokeWidth={1} dot={false} name="Random Forest" />
                                        <Line type="monotone" dataKey="xgboost" stroke="#9b59b6" strokeWidth={1} dot={false} name="XGBoost" />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="voting-section card">
                            <h3><FaCalendarAlt /> Consensus Dashboard</h3>
                            <div className="voting-list">
                                {result.voting.map((vote, idx) => (
                                    <div key={idx} className={`voting-item ${vote.trend.toLowerCase()}`}>
                                        <span className="vote-date">{vote.date}</span>
                                        <span className="vote-trend">
                                            {vote.trend === 'Up' ? <FaArrowUp /> : <FaArrowDown />} {vote.trend}
                                        </span>
                                        <span className="vote-confidence">Confidence: {vote.confidence}%</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FuturePrediction;
