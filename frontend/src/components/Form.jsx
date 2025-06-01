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
    formData.append("dataFile", file); // actual file
    formData.append("startDate", startDate); // other fields
    formData.append("endDate", endDate);

    try {
      const res = await axios.post("http://localhost:5000/run", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      console.log(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <form
      className="form-inline"
      enctype="multipart/form-data"
      onSubmit={handleSubmit}
    >
      <div className="form-group mb-2">
        <label>
          Start Date:{" "}
          <input
            className="form-control"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>
      </div>
      <div className="form-group mb-2">
        <label>
          End Date:{" "}
          <input
            type="date"
            className="form-control"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </label>
      </div>
      <div className="form-group mb-2">
        <label>
          Upload Dataset:
          <input
            type="file"
            className="form-control"
            accept=".csv,.json"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </label>
      </div>
      <div className="form-group mb-2">
        <button className="btn btn-primary mb-2" type="submit">
          Run Algorithm
        </button>
      </div>
    </form>
  );
}

export default Form;
