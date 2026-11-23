// Logged-in start page. Will become the personal feed (F2).
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Home() {
  const { user } = useAuth();
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/health").then(setHealth).catch((err) => setError(err.message));
  }, []);

  return (
    <section>
      <h1>Welcome, {user.name}</h1>
      <p className="muted">
        {user.role}{user.department ? ` · ${user.department}` : ""} · {user.email}
      </p>

      <div className="card">
        <h2>Platform status</h2>
        {error && <p className="error">{error}</p>}
        {!health && !error && <p className="muted">Loading…</p>}
        {health && (
          <ul className="stats">
            {Object.entries(health.row_counts).map(([table, n]) => (
              <li key={table}><strong>{n}</strong> {table}</li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
