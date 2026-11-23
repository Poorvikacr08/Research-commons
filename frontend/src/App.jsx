import { useEffect, useState } from "react";

// Temporary start page: shows whether the front end can reach the API and database.
export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.statusText)))
      .then(setHealth)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto" }}>
      <h1>Chanakya Research Commons</h1>
      {error && <p style={{ color: "crimson" }}>API not reachable: {error}</p>}
      {!health && !error && <p>Connecting to API…</p>}
      {health && (
        <>
          <p>API status: <strong>{health.status}</strong></p>
          <h3>Row counts</h3>
          <ul>
            {Object.entries(health.row_counts).map(([table, n]) => (
              <li key={table}>{table}: {n}</li>
            ))}
          </ul>
          <p>{health.tables.length} tables in the database.</p>
        </>
      )}
    </main>
  );
}
