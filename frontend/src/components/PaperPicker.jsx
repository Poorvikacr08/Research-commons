// Pick papers to attach to a post: tick from your library, or search all papers.
import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function PaperPicker({ selected, onChange }) {
  const [mine, setMine] = useState([]);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);

  useEffect(() => {
    api("/library/mine").then(setMine).catch(() => setMine([]));
  }, []);

  async function search(e) {
    e.preventDefault();
    setResults(q.trim() ? await api(`/papers?q=${encodeURIComponent(q)}`) : []);
  }

  function toggle(paper) {
    onChange(selected.some((p) => p.id === paper.id)
      ? selected.filter((p) => p.id !== paper.id)
      : [...selected, { id: paper.id, title: paper.title }]);
  }

  // my library + search results, without duplicates
  const options = [...mine, ...results.filter((r) => !mine.some((m) => m.id === r.id))];

  return (
    <fieldset className="picker">
      <legend>Attach papers <span className="muted">(optional)</span></legend>
      <div className="search-row">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search papers by title…"
          onKeyDown={(e) => e.key === "Enter" && search(e)} />
        <button type="button" className="secondary" onClick={search}>Search</button>
      </div>
      {options.length === 0 && <p className="muted">Save papers in your Library, or search above.</p>}
      <ul className="plain">
        {options.map((p) => (
          <li key={p.id}>
            <label className="check">
              <input type="checkbox" checked={selected.some((s) => s.id === p.id)} onChange={() => toggle(p)} />
              {p.title} {p.year ? <span className="muted">({p.year})</span> : null}
            </label>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}
