import React, { useState } from "react";
import "./App.css";
import ResultCard from "./components/ResultCard";

function App() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFiles(e.target.files);
    setError(null); // Clear previous errors
  };

  const handleUpload = async () => {
    if (!files || files.length === 0) {
      setError("Please select at least one file");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }

      const response = await fetch("http://localhost:8000/analyze/", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `HTTP error! status: ${response.status}`);
      }

      setResults(data.results || []);
    } catch (err) {
      console.error("Upload error:", err);
      setError(err.message || "An error occurred during upload");
      setResults([]); // Reset results on error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Customer Sentiment Analysis</h1>
        <p>Upload one or more audio files to analyze sentiment and metadata.</p>
      </header>

      <section className="upload-card">
        <input
          className="file-input"
          type="file"
          multiple
          accept="audio/*"
          onChange={handleFileChange}
        />

        <div className="actions">
          <button
            className="btn"
            onClick={handleUpload}
            disabled={loading || !files || files.length === 0}
          >
            {loading ? "Processing..." : "Upload & Analyze"}
          </button>
        </div>

        <div className="hint">
          {files && files.length > 0
            ? `${files.length} file(s) selected`
            : "Supported: wav, mp3, m4a, flac"}
        </div>
      </section>

      {error && (
        <div className="alert error">Error: {error}</div>
      )}

      <h2 className="section-title">Results</h2>
      <div className="results-grid">
        {results && results.length > 0 ? (
          results.map((res, idx) => (
            <ResultCard key={idx} result={res} index={idx} />
          ))
        ) : (
          !loading && !error && (
            <div className="empty">No results yet. Upload files to see analysis.</div>
          )
        )}
      </div>
    </div>
  );
}

export default App;
