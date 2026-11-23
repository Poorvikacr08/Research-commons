// Members directory: search by name, department or interest, and follow people.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import FollowButton from "../components/FollowButton.jsx";
import Tags from "../components/Tags.jsx";

export default function People() {
  const [q, setQ] = useState("");
  const [members, setMembers] = useState(null);
  const [error, setError] = useState("");

  function load(query = "") {
    setError("");
    api(`/users${query ? `?q=${encodeURIComponent(query)}` : ""}`)
      .then(setMembers)
      .catch((err) => setError(err.message));
  }

  useEffect(() => load(), []);

  // update one member's follow state without reloading the list
  function setFollowing(id, value) {
    setMembers((list) => list.map((m) => (m.id === id ? { ...m, is_following: value } : m)));
  }

  return (
    <section>
      <h1>People</h1>
      <form className="search-row" onSubmit={(e) => { e.preventDefault(); load(q); }}>
        <input placeholder="Search name, department or interest…" value={q} onChange={(e) => setQ(e.target.value)} />
        <button type="submit">Search</button>
      </form>

      {error && <p className="error">{error}</p>}
      {!members && !error && <p className="muted">Loading…</p>}
      {members?.length === 0 && <p className="muted">No members found.</p>}

      <div className="list">
        {members?.map((m) => (
          <div key={m.id} className="card row">
            <div>
              <Link to={`/users/${m.id}`} className="name">{m.name}</Link>
              <p className="muted">{m.role}{m.department ? ` · ${m.department}` : ""}</p>
              <Tags tags={m.interests} />
            </div>
            <FollowButton userId={m.id} following={m.is_following} onChange={(v) => setFollowing(m.id, v)} />
          </div>
        ))}
      </div>
    </section>
  );
}
