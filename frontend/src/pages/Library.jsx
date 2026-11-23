// Library: my saved papers, my collections, and the shared Chanakya library.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import PaperCard from "../components/PaperCard.jsx";

export default function Library() {
  const [tab, setTab] = useState("mine");
  return (
    <section>
      <h1>Library</h1>
      <SaveByIdentifier />
      <div className="tabs">
        {[["mine", "My library"], ["collections", "Collections"], ["chanakya", "Chanakya library"]].map(([key, label]) => (
          <button key={key} className={tab === key ? "tab on" : "tab"} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>
      {tab === "mine" && <MyLibrary />}
      {tab === "collections" && <Collections />}
      {tab === "chanakya" && <ChanakyaLibrary />}
    </section>
  );
}

// Paste a URL, DOI or arXiv ID to save a paper.
function SaveByIdentifier() {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await api("/library/save", { method: "POST", body: { identifier: value } }));
      setValue("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <form className="search-row" onSubmit={submit}>
        <input value={value} onChange={(e) => setValue(e.target.value)} required
          placeholder="Save a paper by URL, DOI (10.xxxx/…) or arXiv ID (e.g. 1706.03762)" />
        <button type="submit" disabled={busy}>{busy ? "Finding…" : "Save paper"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && <p className="success">Saved: <Link to={`/papers/${result.id}`}>{result.title}</Link></p>}
    </div>
  );
}

function MyLibrary() {
  const [papers, setPapers] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/library/mine").then(setPapers).catch((err) => setError(err.message));
  }, []);

  // when a paper is unsaved, drop it from the list
  function onChange(updated) {
    setPapers((list) => (updated.is_saved ? list.map((p) => (p.id === updated.id ? updated : p)) : list.filter((p) => p.id !== updated.id)));
  }

  if (error) return <p className="error">{error}</p>;
  if (!papers) return <p className="muted">Loading…</p>;
  if (!papers.length) return <p className="muted">You haven't saved any papers yet. Paste a DOI above, or browse the Chanakya library.</p>;
  return papers.map((p) => <PaperCard key={p.id} paper={p} onChange={onChange} />);
}

function Collections() {
  const [collections, setCollections] = useState(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/collections").then(setCollections).catch((err) => setError(err.message));
  }, []);

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      const c = await api("/collections", { method: "POST", body: { name } });
      setCollections([...collections, c].sort((a, b) => a.name.localeCompare(b.name)));
      setName("");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <form className="search-row" onSubmit={create}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New collection name, e.g. Thesis reading" required />
        <button type="submit">Create collection</button>
      </form>
      {error && <p className="error">{error}</p>}
      {!collections && <p className="muted">Loading…</p>}
      {collections?.length === 0 && <p className="muted">No collections yet.</p>}
      <div className="grid">
        {collections?.map((c) => (
          <Link key={c.id} to={`/collections/${c.id}`} className="card collection-tile">
            <strong>📁 {c.name}</strong>
            <span className="muted">{c.item_count} paper{c.item_count === 1 ? "" : "s"}</span>
          </Link>
        ))}
      </div>
    </>
  );
}

function ChanakyaLibrary() {
  const [sort, setSort] = useState("most_saved");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    api(`/library/chanakya?sort=${sort}&q=${encodeURIComponent(query)}`).then(setData).catch((err) => setError(err.message));
  }, [sort, query]);

  function onChange(updated) {
    setData((d) => ({ ...d, items: d.items.map((p) => (p.id === updated.id ? updated : p)) }));
  }

  return (
    <>
      <form className="search-row" onSubmit={(e) => { e.preventDefault(); setQuery(q); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by title…" />
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="most_saved">Most saved</option>
          <option value="recent">Recently saved</option>
        </select>
        <button type="submit">Filter</button>
      </form>
      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}
      {data && <p className="muted">{data.total_papers} papers saved by Chanakya members</p>}
      {data?.items.length === 0 && <p className="muted">No papers match.</p>}
      {data?.items.map((p) => <PaperCard key={p.id} paper={p} onChange={onChange} />)}
    </>
  );
}
