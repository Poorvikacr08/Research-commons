// Follow / Unfollow a member. Tells the parent the new state via onChange.
import { useState } from "react";
import { api } from "../api.js";

export default function FollowButton({ userId, following, onChange }) {
  const [busy, setBusy] = useState(false);

  async function toggle() {
    setBusy(true);
    try {
      await api(`/users/${userId}/follow`, { method: following ? "DELETE" : "POST" });
      onChange?.(!following);
    } catch (err) {
      alert(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button className={following ? "secondary" : ""} onClick={toggle} disabled={busy}>
      {following ? "Following" : "Follow"}
    </button>
  );
}
