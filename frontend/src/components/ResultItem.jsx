// One search / recommendation result, in the agreed item format:
// { id, type: "paper"|"library"|"person"|"post", title, snippet, sources, score, url, ...extras }
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

function linkFor(item) {
  if (item.type === "person") return `/users/${item.id}`;
  if (item.type === "post") return `/posts/${item.id}`;
  return `/papers/${item.id}`;   // paper or library
}

export default function ResultItem({ item, showSave = false }) {
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    try {
      await api("/library/save", { method: "POST", body: { paper_id: item.id } });
      setSaved(true);
    } catch (err) {
      setError(err.message);
    }
  }

  const meta = [];
  if (item.type === "person") meta.push(item.department);
  if (item.type === "post") meta.push(item.author?.name ?? item.author);
  if (item.sources?.length) meta.push(item.sources.join(" + "));
  if (item.save_count != null) meta.push(`saved by ${item.save_count}`);

  return (
    <li className="result">
      <div className="post-main">
        <Link to={linkFor(item)} className="result-title">{item.title}</Link>
        {meta.filter(Boolean).length > 0 && <p className="muted">{meta.filter(Boolean).join(" · ")}</p>}
        {item.snippet && <p className="snippet">{item.snippet}</p>}
        {item.shared_interests?.length > 0 && (
          <div className="tags">{item.shared_interests.map((t) => <span key={t} className="tag">{t}</span>)}</div>
        )}
        {error && <p className="error">{error}</p>}
      </div>
      {showSave && (item.type === "paper" || item.type === "library") && (
        <button className="secondary small" onClick={save} disabled={saved}>{saved ? "✓ Saved" : "Save"}</button>
      )}
    </li>
  );
}
