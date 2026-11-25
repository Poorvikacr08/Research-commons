// Unified search (F5): one query, four panels. Results come from Member 3's /api/search.
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiOptional } from "../api.js";
import Panel from "../components/Panel.jsx";
import ResultItem from "../components/ResultItem.jsx";

const PANELS = [
  ["external", "📄 Papers"],
  ["library", "📚 Chanakya library"],
  ["people", "👤 People"],
  ["posts", "💬 Posts"],
];

export default function Search() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const [input, setInput] = useState(q);
  const [result, setResult] = useState(null);

  useEffect(() => {
    setInput(q);
    if (!q) return setResult(null);
    setResult(null);
    apiOptional(`/search?q=${encodeURIComponent(q)}`).then(setResult);
  }, [q]);

  // turn the one response into a state for each panel
  function panelState(key) {
    if (!result) return null;
    if (!result.data) return result; // notReady or error -> same for all panels
    if (result.data.errors?.[key]) return { error: result.data.errors[key] };
    return { data: result.data[key] || [] };
  }

  return (
    <section>
      <div className="page-heading">
        <span className="eyebrow">DISCOVER · CONNECT · RESEARCH</span>
        <h1>Ideas take shape here.</h1>
        <p>Explore papers, scholars, and conversations across your research community.</p>
      </div>
      <form className="search-row big" onSubmit={(e) => { e.preventDefault(); setParams(input.trim() ? { q: input.trim() } : {}); }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Search a research topic, e.g. graph neural networks" autoFocus />
        <button type="submit">Search</button>
      </form>

      {!q && <p className="muted">Search once to see papers, the Chanakya library, people and posts on a topic.</p>}

      {q && (
        <div className="search-grid">
          {PANELS.map(([key, title]) => {
            const state = panelState(key);
            return (
              <Panel key={key} title={title} state={state} isEmpty={state?.data?.length === 0} empty="No results.">
                <ul className="results">
                  {state?.data?.map((item) => <ResultItem key={`${item.type}-${item.id}`} item={item} showSave />)}
                </ul>
              </Panel>
            );
          })}
        </div>
      )}
    </section>
  );
}
