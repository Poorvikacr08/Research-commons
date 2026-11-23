// Save / Unsave a paper to my library.
import { useState } from "react";
import { api } from "../api.js";

export default function SaveButton({ paper, onChange }) {
  const [busy, setBusy] = useState(false);

  async function toggle(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const updated = paper.is_saved
        ? await api(`/library/save/${paper.id}`, { method: "DELETE" })
        : await api("/library/save", { method: "POST", body: { paper_id: paper.id } });
      onChange?.(updated);
    } catch (err) {
      alert(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button className={paper.is_saved ? "secondary" : ""} onClick={toggle} disabled={busy}>
      {paper.is_saved ? "✓ Saved" : "Save"}
    </button>
  );
}
