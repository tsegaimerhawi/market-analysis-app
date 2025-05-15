import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [file, setFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Read file as JSON or CSV depending on your use-case
    const reader = new FileReader();
    reader.onload = async () => {
      const text = reader.result;
      const jsonData = {
        startDate,
        endDate,
        data: text // You can parse CSV/JSON here
      };

      try {
        const res = await axios.post('http://localhost:5000/run', jsonData);
        console.log(res.data);
      } catch (err) {
        console.error(err);
      }
    };

    if (file) {
      reader.readAsText(file);
    }
  };

  return (
    <div>
      <h1>Market Analysis</h1>
      <form onSubmit={handleSubmit}>
        <label>Start Date: <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></label><br />
        <label>End Date: <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></label><br />
        <label>Upload Dataset:
          <input type="file" accept=".csv,.json" onChange={(e) => setFile(e.target.files[0])} />
        </label><br />
        <button type="submit">Run Algorithm</button>
      </form>
    </div>
  );
}

export default App;
