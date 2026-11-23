// One post in a list (feed, tag page, profile).
import { Link } from "react-router-dom";
import { timeAgo } from "../utils.js";
import UpvoteButton from "./UpvoteButton.jsx";

export default function PostCard({ post }) {
  return (
    <article className="card post-card">
      <UpvoteButton postId={post.id} upvotes={post.upvotes} hasUpvoted={post.has_upvoted} />
      <div className="post-main">
        {post.reason && <p className="reason">{post.reason}</p>}
        <Link to={`/posts/${post.id}`} className="post-title">{post.title}</Link>
        <p className="muted">
          <Link to={`/users/${post.author.id}`}>{post.author.name}</Link>
          {post.author.department ? ` · ${post.author.department}` : ""} · {timeAgo(post.created_at)}
        </p>
        <p className="snippet">{post.snippet}</p>
        <div className="post-foot">
          <div className="tags">
            {post.tags.map((t) => <Link key={t} to={`/tags/${encodeURIComponent(t)}`} className="tag">{t}</Link>)}
          </div>
          <Link to={`/posts/${post.id}`} className="muted">💬 {post.comment_count}</Link>
        </div>
      </div>
    </article>
  );
}
