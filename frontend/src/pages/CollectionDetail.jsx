// One of my collections: its papers and my private notes on each.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import PaperCard from "../components/PaperCard.jsx";

export default function CollectionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [col, setCol] = useState(null);
  const [error, setError] = useState("");

  function load() {
    api(`/collections/${id}`).then(setCol).catch((err) => setError(err.message));
  }
  useEffect(load, [id]);

  async function removeItem(paperId) {
    await api(`/collections/${id}/items/${paperId}`, { method: "DELETE" });
    load();
  }

  async function deleteCollection() {
    if (!confirm(`Delete "${col.name}"? The papers stay in your library.`)) return;
    await api(`/collections/${id}`, { method: "DELETE" });
    navigate("/library");
  }

  if (error) return <p className="error">{error}</p>;
  if (!col) return <p className="muted">Loading…</p>;

  return (
    <section>
      <p><Link to="/library">← Library</Link></p>
      <div className="row">
        <h1>📁 {col.name}</h1>
        <button className="link-button danger" onClick={deleteCollection}>Delete collection</button>
      </div>
      <p className="muted">{col.item_count} paper{col.item_count === 1 ? "" : "s"} · notes are private to you</p>
      {col.items.length === 0 && <p className="muted">Empty. Open any paper and use "Add to a collection".</p>}
      {col.items.map((item) => (
        <PaperCard key={item.id} paper={item} onChange={load}>
          <NoteEditor collectionId={id} item={item} />
          <button className="link-button" onClick={() => removeItem(item.id)}>Remove from collection</button>
        </PaperCard>
      ))}
    </section>
  );
}

function NoteEditor({ collectionId, item }) {
  const [note, setNote] = useState(item.note || "");
  const [status, setStatus] = useState("");

  async function save() {
    setStatus("Saving…");
    try {
      await api(`/collections/${collectionId}/items/${item.id}`, { method: "PUT", body: { note } });
      setStatus("Saved");
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <div className="note-editor">
      <textarea rows={2} value={note} onChange={(e) => { setNote(e.target.value); setStatus(""); }} placeholder="Private note…" />
      <div className="row-start">
        <button className="secondary" onClick={save} disabled={note === (item.note || "") && !status}>Save note</button>
        <span className="muted">{status}</span>
      </div>
    </div>
  );
}
