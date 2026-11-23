// ▲ 12  - click to upvote, click again to remove.
import { useState } from "react";
import { api } from "../api.js";

export default function UpvoteButton({ postId, upvotes, hasUpvoted }) {
  const [state, setState] = useState({ upvotes, has_upvoted: hasUpvoted });
  const [busy, setBusy] = useState(false);

  async function toggle(e) {
    e.preventDefault(); // the button may sit inside a link
    setBusy(true);
    try {
      const next = await api(`/posts/${postId}/upvote`, { method: state.has_upvoted ? "DELETE" : "POST" });
      setState(next);
    } catch (err) {
      alert(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      className={`upvote ${state.has_upvoted ? "on" : ""}`}
      onClick={toggle}
      disabled={busy}
      title={state.has_upvoted ? "Remove upvote" : "Upvote"}
    >
      ▲ {state.upvotes}
    </button>
  );
}
