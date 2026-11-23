// A member's profile. On your own profile you also manage the topics you follow.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import FollowButton from "../components/FollowButton.jsx";
import PostCard from "../components/PostCard.jsx";
import Tags from "../components/Tags.jsx";

export default function Profile() {
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setProfile(null);
    setError("");
    api(`/users/${id}`).then(setProfile).catch((err) => setError(err.message));
  }, [id]);

  function onFollowChange(following) {
    setProfile((p) => ({
      ...p,
      is_following: following,
      followers_count: p.followers_count + (following ? 1 : -1),
    }));
  }

  if (error) return <p className="error">{error}</p>;
  if (!profile) return <p className="muted">Loading…</p>;

  return (
    <section>
      <div className="card">
        <div className="row">
          <div>
            <h1>{profile.name}</h1>
            <p className="muted">{profile.role}{profile.department ? ` · ${profile.department}` : ""} · {profile.email}</p>
          </div>
          {profile.is_me
            ? <Link to="/profile/edit" className="button">Edit profile</Link>
            : <FollowButton userId={profile.id} following={profile.is_following} onChange={onFollowChange} />}
        </div>

        <p className="counts">
          <strong>{profile.followers_count}</strong> followers · <strong>{profile.following_count}</strong> following
        </p>

        {profile.bio && <p>{profile.bio}</p>}
        {profile.links && (
          <p><a href={profile.links} target="_blank" rel="noreferrer">{profile.links}</a></p>
        )}

        <h3>Research interests</h3>
        <Tags tags={profile.interests} />
      </div>

      {profile.is_me && <MyTopics />}
      <UserPosts userId={profile.id} />
    </section>
  );
}

// Posts written by this member
function UserPosts({ userId }) {
  const [posts, setPosts] = useState(null);
  useEffect(() => {
    api(`/posts?author_id=${userId}`).then(setPosts).catch(() => setPosts([]));
  }, [userId]);
  if (!posts) return null;
  return (
    <>
      <h2 className="section-title">Posts ({posts.length})</h2>
      {posts.length === 0 && <p className="muted">No posts yet.</p>}
      {posts.map((p) => <PostCard key={p.id} post={p} />)}
    </>
  );
}

// Follow / unfollow topics (only shown on your own profile)
function MyTopics() {
  const [topics, setTopics] = useState([]);
  const [newTopic, setNewTopic] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/topics/following").then((d) => setTopics(d.topics)).catch((err) => setError(err.message));
  }, []);

  async function add(e) {
    e.preventDefault();
    if (!newTopic.trim()) return;
    try {
      const d = await api(`/topics/${encodeURIComponent(newTopic)}/follow`, { method: "POST" });
      setTopics(d.topics);
      setNewTopic("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(tag) {
    const d = await api(`/topics/${encodeURIComponent(tag)}/follow`, { method: "DELETE" });
    setTopics(d.topics);
  }

  return (
    <div className="card">
      <h3>Topics I follow</h3>
      {error && <p className="error">{error}</p>}
      <div className="tags">
        {topics.length === 0 && <span className="muted">Not following any topics yet.</span>}
        {topics.map((t) => (
          <span key={t} className="tag">
            {t} <button className="tag-x" onClick={() => remove(t)} aria-label={`Unfollow ${t}`}>×</button>
          </span>
        ))}
      </div>
      <form className="search-row" onSubmit={add}>
        <input placeholder="Follow a topic, e.g. machine learning" value={newTopic} onChange={(e) => setNewTopic(e.target.value)} />
        <button type="submit">Follow topic</button>
      </form>
    </div>
  );
}
