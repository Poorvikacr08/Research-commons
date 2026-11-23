// Shows a list of tags as small chips.
export default function Tags({ tags, empty = "No interests yet" }) {
  if (!tags?.length) return <span className="muted">{empty}</span>;
  return (
    <div className="tags">
      {tags.map((t) => <span key={t} className="tag">{t}</span>)}
    </div>
  );
}
