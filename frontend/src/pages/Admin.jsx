// Admin only: spam / abnormal activity flags and topic spike alerts (F7, Member 3).
// The F9 analytics dashboard (Member 2) will be added here.
import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { apiOptional } from "../api.js";
import { useAuth } from "../auth.jsx";
import Panel from "../components/Panel.jsx";
import { timeAgo } from "../utils.js";

export default function Admin() {
  const { user } = useAuth();
  const [flags, setFlags] = useState(null);
  const [trends, setTrends] = useState(null);

  useEffect(() => {
    if (user.role !== "admin") return;
    apiOptional("/admin/flags").then(setFlags);
    apiOptional("/trends?days=7").then(setTrends);
  }, [user.role]);

  if (user.role !== "admin") return <Navigate to="/" replace />;

  const spikes = trends?.data ? { data: trends.data.items.filter((t) => t.is_spike) } : trends;

  return (
    <section>
      <h1>Admin</h1>

      <Panel title="🚩 Flagged accounts (spam / abnormal activity)" state={flags} isEmpty={flags?.data?.items.length === 0} empty="No accounts flagged.">
        <table className="table">
          <thead><tr><th>Member</th><th>Reason</th><th>Score</th><th>Flagged</th></tr></thead>
          <tbody>
            {flags?.data?.items.map((f) => (
              <tr key={f.user_id}>
                <td><Link to={`/users/${f.user_id}`}>{f.name}</Link></td>
                <td>{f.reason}</td>
                <td>{f.score?.toFixed(2)}</td>
                <td className="muted">{f.flagged_at ? timeAgo(f.flagged_at) : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="📈 Topic spike alerts (last 7 days)" state={spikes} isEmpty={spikes?.data?.length === 0} empty="No unusual spikes.">
        <ul className="plain trend-list">
          {spikes?.data?.map((t) => (
            <li key={t.tag}>
              <Link to={`/tags/${encodeURIComponent(t.tag)}`} className="tag">{t.tag}</Link>
              <span className="muted">{t.count} this week{t.change_pct != null && ` · ▲ ${Math.round(t.change_pct)}%`}</span>
            </li>
          ))}
        </ul>
      </Panel>

      <div className="card">
        <h3>📊 Analytics dashboard</h3>
        <p className="muted">Topics by department over time, cross-department activity and most-saved papers — coming from the analytics service.</p>
      </div>
    </section>
  );
}
