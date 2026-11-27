// One paper: details, abstract, save, add to a collection with a private note.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, apiOptional } from "../api.js";
import Panel from "../components/Panel.jsx";
import KnowledgeThread from "../components/KnowledgeThread.jsx";
import ResultItem from "../components/ResultItem.jsx";
import SaveButton from "../components/SaveButton.jsx";

export default function PaperDetail() {
  const { id } = useParams();
  const [paper, setPaper] = useState(null);
  const [error, setError] = useState("");

  function load() {
    api(`/papers/${id}`).then(setPaper).catch((err) => setError(err.message));
  }
  useEffect(load, [id]);

  if (error) return <p className="error">{error}</p>;
  if (!paper) return <p className="muted">Loading…</p>;

  const link = paper.url || (paper.doi ? `https://doi.org/${paper.doi}` : null);

  return (
    <section>
      <article className="card">
        <div className="row">
          <h1>{paper.title}</h1>
          <SaveButton paper={paper} onChange={(u) => setPaper((p) => ({
            ...p, ...u,
            // unsaving also removes it from my collections
            my_collections: u.is_saved ? p.my_collections : [],
            my_notes: u.is_saved ? p.my_notes : {},
          }))} />
        </div>
        <p className="muted">{[paper.authors, paper.year, paper.source].filter(Boolean).join(" · ")}</p>
        <p className="saved-by">📚 Saved by {paper.save_count} Chanakya member{paper.save_count === 1 ? "" : "s"}</p>
        {paper.abstract && (<><h3>Abstract</h3><p className="body">{paper.abstract}</p></>)}
        <p className="muted">
          {paper.doi && <>DOI: {paper.doi} · </>}
          {paper.arxiv_id && <>arXiv: {paper.arxiv_id} · </>}
          {link && <a href={link} target="_blank" rel="noreferrer">Open paper ↗</a>}
        </p>
      </article>

      <KnowledgeThread paper={paper} />
      <AddToCollection paper={paper} onDone={load} />
      <AlsoSaved paperId={paper.id} />

      {paper.my_collections.length > 0 && (
        <div className="card">
          <h3>In your collections</h3>
          <ul className="plain">
            {paper.my_collections.map((c) => (
              <li key={c.id}>
                <Link to={`/collections/${c.id}`}>📁 {c.name}</Link>
                {paper.my_notes[c.id] && <p className="note">📝 {paper.my_notes[c.id]}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function AddToCollection({ paper, onDone }) {
  const [collections, setCollections] = useState([]);
  const [collectionId, setCollectionId] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api("/collections").then((cs) => {
      setCollections(cs);
      if (cs.length) setCollectionId(cs[0].id);
    });
  }, []);

  async function add(e) {
    e.preventDefault();
    try {
      await api(`/collections/${collectionId}/items`, { method: "POST", body: { paper_id: paper.id, note } });
      setNote("");
      setMessage("Added.");
      onDone();
    } catch (err) {
      setMessage(err.message);
    }
  }

  if (!collections.length) {
    return <p className="muted">Create a collection in the <Link to="/library">Library</Link> to organise this paper with private notes.</p>;
  }
  return (
    <form className="card form" onSubmit={add}>
      <h3>Add to a collection</h3>
      <select value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
        {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Private note (only you can see it)" />
      <div className="row-start">
        <button type="submit">Add</button>
        {message && <span className="muted">{message}</span>}
      </div>
    </form>
  );
}

// F6 (Member 3): papers that members who saved this one also saved
function AlsoSaved({ paperId }) {
  const [state, setState] = useState(null);
  useEffect(() => {
    setState(null);
    apiOptional(`/papers/${paperId}/also-saved?limit=5`).then(setState);
  }, [paperId]);
  return (
    <Panel title="Members who saved this also saved" state={state} isEmpty={state?.data?.items.length === 0} empty="Not enough saves yet.">
      <ul className="results">{state?.data?.items.map((i) => <ResultItem key={i.id} item={i} showSave />)}</ul>
    </Panel>
  );
}
