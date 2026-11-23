// All posts with one tag, plus a button to follow the topic.
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import PostCard from "../components/PostCard.jsx";

export default function TagPage() {
  const { tag } = useParams();
  const [posts, setPosts] = useState(null);
  const [following, setFollowing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setPosts(null);
    api(`/posts?tag=${encodeURIComponent(tag)}`).then(setPosts).catch((err) => setError(err.message));
    api("/topics/following").then((d) => setFollowing(d.topics.includes(tag.toLowerCase())));
  }, [tag]);

  async function toggleFollow() {
    const d = await api(`/topics/${encodeURIComponent(tag)}/follow`, { method: following ? "DELETE" : "POST" });
    setFollowing(d.topics.includes(tag.toLowerCase()));
  }

  return (
    <section>
      <div className="row">
        <h1>#{tag}</h1>
        <button className={following ? "secondary" : ""} onClick={toggleFollow}>
          {following ? "Following topic" : "Follow topic"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {!posts && !error && <p className="muted">Loading…</p>}
      {posts?.length === 0 && <p className="muted">No posts with this tag yet.</p>}
      {posts?.map((p) => <PostCard key={p.id} post={p} />)}
    </section>
  );
}
