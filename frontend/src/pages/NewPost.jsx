// Write a post: title, text, tags and (optionally) papers from the library.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import PaperPicker from "../components/PaperPicker.jsx";
import { splitTags } from "../utils.js";

export default function NewPost() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: "", body: "", tags: "" });
  const [papers, setPapers] = useState([]); // [{ id, title }]
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const post = await api("/posts", { method: "POST", body: { ...form, tags: splitTags(form.tags), paper_ids: papers.map((p) => p.id) } });
      navigate(`/posts/${post.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <h1>New post</h1>
      {error && <p className="error">{error}</p>}
      <label>Title<input name="title" value={form.title} onChange={update} maxLength={200} required autoFocus /></label>
      <label>What's your idea or question?<textarea name="body" rows={7} value={form.body} onChange={update} required /></label>
      <label>
        Tags <span className="muted">(separate with commas)</span>
        <input name="tags" value={form.tags} onChange={update} placeholder="machine learning, healthcare" />
      </label>
      <PaperPicker selected={papers} onChange={setPapers} />
      <div className="row-start">
        <button type="submit" disabled={busy}>{busy ? "Posting…" : "Post"}</button>
        <button type="button" className="secondary" onClick={() => navigate(-1)}>Cancel</button>
      </div>
    </form>
  );
}
