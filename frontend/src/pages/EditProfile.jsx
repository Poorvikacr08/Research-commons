// Edit your own profile: name, department, bio, link and research interests.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function EditProfile() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // load current values into the form
  useEffect(() => {
    api(`/users/${user.id}`)
      .then((p) => setForm({
        name: p.name,
        department: p.department || "",
        bio: p.bio || "",
        links: p.links || "",
        interests: p.interests.join(", "), // shown as comma-separated text
      }))
      .catch((err) => setError(err.message));
  }, [user.id]);

  function update(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const saved = await api("/users/me", {
        method: "PUT",
        body: { ...form, interests: form.interests.split(",") },
      });
      setUser({ ...user, name: saved.name, department: saved.department });
      navigate(`/users/${user.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!form) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <h1>Edit profile</h1>
      {error && <p className="error">{error}</p>}

      <label>Full name<input name="name" value={form.name} onChange={update} required /></label>
      <label>Department<input name="department" value={form.department} onChange={update} /></label>
      <label>About you<textarea name="bio" rows={3} value={form.bio} onChange={update} /></label>
      <label>Publications / personal page (link)<input name="links" type="url" value={form.links} onChange={update} placeholder="https://…" /></label>
      <label>
        Research interests <span className="muted">(separate with commas)</span>
        <input name="interests" value={form.interests} onChange={update} placeholder="machine learning, nlp, data mining" />
      </label>

      <div className="row-start">
        <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        <button type="button" className="secondary" onClick={() => navigate(-1)}>Cancel</button>
      </div>
    </form>
  );
}
