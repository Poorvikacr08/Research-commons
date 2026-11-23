// F9 analytics dashboard (admin). Data comes from Member 2's analytics service:
//   GET /api/analytics/overview
//   GET /api/analytics/topics?department=&tag=&months=6
// Drill-down: university -> department -> topic -> member.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { apiOptional } from "../api.js";
import Panel from "./Panel.jsx";

// Validated categorical order (colour-blind safe for adjacent series). Max 4 lines.
const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"];
const BAR = "#2a78d6";
const GRID = "#e1e0d9";
const MUTED = "#898781";
const BLUES = ["#f4f8fe", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]; // sequential

const fmt = (n) => (n >= 10000 ? `${(n / 1000).toFixed(n >= 100000 ? 0 : 1)}K` : n.toLocaleString());

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  return (
    <>
      <Overview onLoad={setOverview} />
      <TopicExplorer />
      <div className="dash-two">
        <CrossDepartment state={overview} />
        <MostSaved state={overview} />
      </div>
    </>
  );
}

// ---------- KPI tiles ----------
function Overview({ onLoad }) {
  const [state, setState] = useState(null);
  useEffect(() => {
    apiOptional("/analytics/overview").then((s) => { setState(s); onLoad(s); });
  }, []);
  const k = state?.data?.kpis;
  const tiles = k ? [
    ["Members", k.members], ["Papers", k.papers], ["Posts", k.posts], ["Comments", k.comments], ["Saves (last 30 days)", k.saves_30d],
  ] : [];
  return (
    <Panel title="📊 Platform overview" state={state}>
      <div className="kpis">
        {tiles.map(([label, value]) => (
          <div key={label} className="kpi"><span className="kpi-label">{label}</span><span className="kpi-value">{fmt(value ?? 0)}</span></div>
        ))}
      </div>
    </Panel>
  );
}

// ---------- topics over time + drill-down ----------
function TopicExplorer() {
  const [scope, setScope] = useState({});          // {} -> {department} -> {department, tag}
  const [state, setState] = useState(null);
  const [showTable, setShowTable] = useState(false);
  const [loading, setLoading] = useState(false);

  // keep showing the previous level while the next one loads (no flicker)
  useEffect(() => {
    setLoading(true);
    const q = new URLSearchParams({ months: "6", ...scope }).toString();
    apiOptional(`/analytics/topics?${q}`).then((s) => { setState(s); setLoading(false); });
  }, [scope.department, scope.tag]);

  const d = state?.data;
  const series = (d?.series || []).slice(0, 4);    // never more than 4 lines
  const rows = (d?.periods || []).map((period, i) => {
    const row = { period };
    series.forEach((s) => { row[s.key] = s.counts[i] ?? 0; });
    return row;
  });
  // label a line's end only if no other line ends close to it (labels must never collide;
  // the legend above always identifies every line)
  const ends = series.map((s) => s.counts[rows.length - 1] ?? 0);
  const span = Math.max(1, ...ends) - Math.min(0, ...ends);
  const labelEnd = series.map((_, i) => ends.every((v, j) => j === i || Math.abs(v - ends[i]) / span > 0.08));
  const dimension = d?.breakdown?.dimension;       // "department" | "topic" | "member"
  const items = d?.breakdown?.items || [];

  function drill(item) {
    if (dimension === "department") setScope({ department: item.key });
    else if (dimension === "topic") setScope({ ...scope, tag: item.key });
  }

  const crumbs = [["Chanakya University", {}]];
  if (scope.department) crumbs.push([scope.department, { department: scope.department }]);
  if (scope.tag) crumbs.push([`#${scope.tag}`, scope]);

  return (
    <Panel title="🔎 Research topics over time" state={state} isEmpty={!rows.length && !items.length} empty="No activity in this period.">
      <nav className="crumbs">
        {crumbs.map(([label, s], i) => (
          <span key={label}>
            {i > 0 && " › "}
            {i < crumbs.length - 1 ? <button className="link-button" onClick={() => setScope(s)}>{label}</button> : <strong>{label}</strong>}
          </span>
        ))}
        {loading && <span className="muted"> · Loading…</span>}
      </nav>

      {series.length > 0 && (
        <>
          <div className="legend">
            {series.map((s, i) => <span key={s.key}><i style={{ background: SERIES[i] }} />{s.label}</span>)}
            <button className="link-button small-text" onClick={() => setShowTable(!showTable)}>{showTable ? "Show chart" : "Show table"}</button>
          </div>
          {showTable ? (
            <table className="table">
              <thead><tr><th>Month</th>{series.map((s) => <th key={s.key}>{s.label}</th>)}</tr></thead>
              <tbody>{rows.map((r) => <tr key={r.period}><td>{r.period}</td>{series.map((s) => <td key={s.key}>{r[s.key]}</td>)}</tr>)}</tbody>
            </table>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={rows} margin={{ top: 10, right: 110, bottom: 0, left: -10 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="period" tick={{ fill: MUTED, fontSize: 12 }} axisLine={{ stroke: GRID }} tickLine={false} />
                <YAxis tick={{ fill: MUTED, fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} tickFormatter={fmt} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }} />
                {series.map((s, i) => (
                  <Line key={s.key} dataKey={s.key} name={s.label} stroke={SERIES[i]} strokeWidth={2} isAnimationActive={false}
                    dot={false} activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2 }}>
                    {/* direct label at the line end, in text colour (not the series colour) */}
                    <LabelList dataKey={s.key} content={(p) => p.index === rows.length - 1 && labelEnd[i]
                      ? <text x={p.x + 8} y={p.y + 4} fontSize={12} fill="#52514e">{s.label}</text> : null} />
                  </Line>
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </>
      )}

      {items.length > 0 && (
        <>
          <h4 className="dash-sub">
            {dimension === "department" && "Activity by department — click to drill down"}
            {dimension === "topic" && "Top topics — click to drill down"}
            {dimension === "member" && "Most active members on this topic"}
          </h4>
          <ResponsiveContainer width="100%" height={Math.max(120, items.length * 34)}>
            <BarChart data={items} layout="vertical" margin={{ top: 0, right: 50, bottom: 0, left: 10 }} barCategoryGap={8}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" width={150} tick={{ fill: "#52514e", fontSize: 13 }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#f3f4f6" }} contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }} />
              <Bar dataKey="count" name="Activity" fill={BAR} barSize={18} radius={[0, 4, 4, 0]} isAnimationActive={false}
                cursor={dimension === "member" ? "default" : "pointer"} onClick={(row) => drill(row.payload ?? row)}>
                <LabelList dataKey="count" position="right" fill="#52514e" fontSize={12} formatter={fmt} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {dimension === "member" && (
            <p className="muted">
              Open a profile: {items.map((m, i) => <span key={m.key}>{i > 0 && ", "}<Link to={`/users/${m.key}`}>{m.label}</Link></span>)}
            </p>
          )}
        </>
      )}
    </Panel>
  );
}

// ---------- department x department matrix ----------
function CrossDepartment({ state }) {
  const pairs = state?.data?.cross_department || [];
  const depts = [...new Set(pairs.flatMap((p) => [p.from_department, p.to_department]))].sort();
  const max = Math.max(1, ...pairs.map((p) => p.count));
  const lookup = Object.fromEntries(pairs.map((p) => [`${p.from_department}|${p.to_department}`, p.count]));
  const shade = (n) => BLUES[Math.min(BLUES.length - 1, Math.round((n / max) * (BLUES.length - 1)))];

  return (
    <Panel title="🔗 Cross-department activity" state={state} isEmpty={!pairs.length} empty="No cross-department activity yet.">
      <p className="muted">Row members saving / commenting on work from the column department.</p>
      <div className="matrix-wrap">
        <table className="matrix">
          <thead><tr><th />{depts.map((d) => <th key={d} title={d}>{d}</th>)}</tr></thead>
          <tbody>
            {depts.map((from) => (
              <tr key={from}>
                <th>{from}</th>
                {depts.map((to) => {
                  const n = lookup[`${from}|${to}`] || 0;
                  const bg = shade(n);
                  const dark = BLUES.indexOf(bg) >= 4;
                  return <td key={to} title={`${from} → ${to}: ${n}`} style={{ background: bg, color: dark ? "#fff" : "#0b0b0b" }}>{n || ""}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

// ---------- most saved papers ----------
function MostSaved({ state }) {
  const papers = state?.data?.top_saved || [];
  return (
    <Panel title="📚 Most-saved papers" state={state} isEmpty={!papers.length} empty="No saves yet.">
      <ol className="top-saved">
        {papers.slice(0, 8).map((p) => (
          <li key={p.paper_id}>
            <Link to={`/papers/${p.paper_id}`}>{p.title}</Link>
            <span className="muted">{p.save_count} saves</span>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
