import React, { useState } from "react";
import axios from "axios";

function Form() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [file, setFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      alert("Please select a file");
      return;
    }

    const formData = new FormData();
    formData.append("dataFile", file);
    formData.append("startDate", startDate);
    formData.append("endDate", endDate);

    try {
      const res = await axios.post(
        "http://localhost:5001/stock_prediction/run_bayesian",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      console.log(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <form className="container mt-4" onSubmit={handleSubmit}>
      <div className="d-flex flex-wrap align-items-end gap-3">
        <div className="form-group">
          <label htmlFor="startDate">Start Date</label>
          <input
            id="startDate"
            className="form-control"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label htmlFor="endDate">End Date</label>
          <input
            id="endDate"
            className="form-control"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label htmlFor="fileInput">Upload Dataset</label>
          <input
            id="fileInput"
            type="file"
            className="form-control"
            accept=".csv,.json"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </div>

        <div className="form-group mt-4">
          <button className="btn btn-primary" type="submit">
            Run Algorithm
          </button>
        </div>
      </div>
    </form>
  );
}

export default Form;
