// Personal feed: "Following" = people/topics you follow + your interests; "All posts" = everything.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import PostCard from "../components/PostCard.jsx";
import Sidebar from "../components/Sidebar.jsx";

export default function Home() {
  const { user } = useAuth();
  const [tab, setTab] = useState("following");
  const [feed, setFeed] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setFeed(null);
    setError("");
    api(`/feed?tab=${tab}`).then(setFeed).catch((err) => setError(err.message));
  }, [tab]);

  return (
    <div className="home-layout">
    <section className="research-masthead" aria-label="Research community">
      <div className="research-masthead-copy">
        <span className="eyebrow">CHANAKYA SCHOLARSPHERE · RESEARCH COMMUNITY</span>
        <h1>Ideas rooted in wisdom.<br /><em>Research moving forward.</em></h1>
        <p>Discover scholarship, exchange perspectives, and find the people who make research richer.</p>
        <Link to="/search" className="button">Explore research <span aria-hidden="true">↗</span></Link>
      </div>
      <div className="research-masthead-image" role="img" aria-label="Chanakya University campus">
        <span>CHANAKYA UNIVERSITY <i>·</i> GLOBAL CAMPUS</span>
      </div>
    </section>
    <div className="with-sidebar">
    <section>
      <div className="row">
        <h1>Hi, {user.name}</h1>
        <Link to="/posts/new" className="button">+ New post</Link>
      </div>

      <div className="tabs">
        <button className={tab === "following" ? "tab on" : "tab"} onClick={() => setTab("following")}>For you</button>
        <button className={tab === "all" ? "tab on" : "tab"} onClick={() => setTab("all")}>All posts</button>
      </div>

      {error && <p className="error">{error}</p>}
      {!feed && !error && <p className="muted">Loading…</p>}

      {feed?.strategy === "popular" && feed.items.length > 0 && (
        <p className="notice">
          You're not following anyone yet, so here are popular posts.{" "}
          <Link to="/people">Find people</Link> or add interests on your <Link to={`/users/${user.id}`}>profile</Link>.
        </p>
      )}
      {feed?.items.length === 0 && (
        <p className="muted">No posts yet. <Link to="/posts/new">Write the first one</Link>.</p>
      )}

      {feed?.items.map((p) => <PostCard key={p.id} post={p} />)}
    </section>
    <Sidebar />
    </div>
    </div>
  );
}
