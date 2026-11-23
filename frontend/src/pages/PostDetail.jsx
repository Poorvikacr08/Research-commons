// One post with its papers, upvotes and the discussion (comments + nested replies).
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import UpvoteButton from "../components/UpvoteButton.jsx";
import { timeAgo } from "../utils.js";

export default function PostDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setPost(null);
    api(`/posts/${id}`).then(setPost).catch((err) => setError(err.message));
  }, [id]);

  function addComment(comment) {
    setPost((p) => ({ ...p, comments: [...p.comments, comment], comment_count: p.comment_count + 1 }));
  }

  async function handleDelete() {
    if (!confirm("Delete this post?")) return;
    await api(`/posts/${id}`, { method: "DELETE" });
    navigate("/");
  }

  if (error) return <p className="error">{error}</p>;
  if (!post) return <p className="muted">Loading…</p>;

  // group comments by the comment they reply to (null = top level)
  const byParent = {};
  for (const c of post.comments) (byParent[c.parent_id ?? "root"] ??= []).push(c);

  return (
    <section>
      <article className="card post-card">
        <UpvoteButton postId={post.id} upvotes={post.upvotes} hasUpvoted={post.has_upvoted} />
        <div className="post-main">
          <h1>{post.title}</h1>
          <p className="muted">
            <Link to={`/users/${post.author.id}`}>{post.author.name}</Link>
            {post.author.department ? ` · ${post.author.department}` : ""} · {timeAgo(post.created_at)}
          </p>
          <p className="body">{post.body}</p>
          <div className="tags">
            {post.tags.map((t) => <Link key={t} to={`/tags/${encodeURIComponent(t)}`} className="tag">{t}</Link>)}
          </div>
          {post.papers.length > 0 && (
            <div className="papers">
              <h3>Attached papers</h3>
              <ul>{post.papers.map((p) => <li key={p.id}>📄 {p.title}</li>)}</ul>
            </div>
          )}
          {post.can_delete && <button className="link-button danger" onClick={handleDelete}>Delete post</button>}
        </div>
      </article>

      <div className="card">
        <h2>Discussion ({post.comment_count})</h2>
        <CommentForm postId={post.id} onAdded={addComment} />
        <CommentList parentKey="root" byParent={byParent} postId={post.id} onAdded={addComment} />
      </div>
    </section>
  );
}

// Shows comments under one parent, and their replies underneath (indented).
function CommentList({ parentKey, byParent, postId, onAdded }) {
  const list = byParent[parentKey] || [];
  if (!list.length) return null;
  return (
    <ul className={parentKey === "root" ? "comments" : "comments replies"}>
      {list.map((c) => (
        <Comment key={c.id} comment={c} postId={postId} onAdded={onAdded}>
          <CommentList parentKey={c.id} byParent={byParent} postId={postId} onAdded={onAdded} />
        </Comment>
      ))}
    </ul>
  );
}

function Comment({ comment, postId, onAdded, children }) {
  const [replying, setReplying] = useState(false);
  return (
    <li className="comment">
      <p className="muted">
        <Link to={`/users/${comment.author.id}`}>{comment.author.name}</Link> · {timeAgo(comment.created_at)}
      </p>
      <p>{comment.body}</p>
      <button className="link-button" onClick={() => setReplying(!replying)}>{replying ? "Cancel" : "Reply"}</button>
      {replying && (
        <CommentForm postId={postId} parentId={comment.id} onAdded={(c) => { onAdded(c); setReplying(false); }} />
      )}
      {children}
    </li>
  );
}

function CommentForm({ postId, parentId = null, onAdded }) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    setError("");
    try {
      const comment = await api(`/posts/${postId}/comments`, { method: "POST", body: { body, parent_id: parentId } });
      onAdded(comment);
      setBody("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="comment-form" onSubmit={submit}>
      {error && <p className="error">{error}</p>}
      <textarea rows={parentId ? 2 : 3} value={body} onChange={(e) => setBody(e.target.value)}
        placeholder={parentId ? "Write a reply…" : "Add to the discussion…"} />
      <button type="submit" disabled={busy || !body.trim()}>{parentId ? "Reply" : "Comment"}</button>
    </form>
  );
}
