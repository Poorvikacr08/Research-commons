// Home page sidebar: recommendations (F6) and trending tags (F7) from Member 3.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiOptional } from "../api.js";
import Panel from "./Panel.jsx";
import ResultItem from "./ResultItem.jsx";

// strategy "personalized" -> "For you"; "popular" (new users) -> "Popular in your department"
function heading(base, state, popularLabel) {
  return state?.data?.strategy === "popular" ? popularLabel : base;
}

export default function Sidebar() {
  const [papers, setPapers] = useState(null);
  const [people, setPeople] = useState(null);
  const [trends, setTrends] = useState(null);

  useEffect(() => {
    apiOptional("/recommend/papers?limit=5").then(setPapers);
    apiOptional("/recommend/people?limit=5").then(setPeople);
    apiOptional("/trends?days=7").then(setTrends);
  }, []);

  return (
    <aside className="sidebar">
      <Panel title={heading("Papers for you", papers, "Popular papers in your department")} state={papers}
        isEmpty={papers?.data?.items.length === 0} empty="Save a few papers to get suggestions.">
        <ul className="results compact">{papers?.data?.items.map((i) => <ResultItem key={i.id} item={i} />)}</ul>
      </Panel>

      <Panel title={heading("People to connect with", people, "Active in your department")} state={people}
        isEmpty={people?.data?.items.length === 0} empty="Add interests to your profile to get suggestions.">
        <ul className="results compact">{people?.data?.items.map((i) => <ResultItem key={i.id} item={i} />)}</ul>
      </Panel>

      <Panel title="Trending this week" state={trends} isEmpty={trends?.data?.items.length === 0} empty="Not enough activity yet.">
        <ul className="plain trend-list">
          {trends?.data?.items.map((t) => (
            <li key={t.tag}>
              <Link to={`/tags/${encodeURIComponent(t.tag)}`} className="tag">{t.tag}</Link>
              <span className="muted">
                {t.count}
                {t.change_pct != null && ` · ${t.change_pct > 0 ? "▲" : "▼"} ${Math.abs(Math.round(t.change_pct))}%`}
              </span>
              {t.is_spike && <span className="spike">spike</span>}
            </li>
          ))}
        </ul>
      </Panel>
    </aside>
  );
}
