// A box that handles the four states every teammate feature can be in:
// loading · not built yet · error · empty  -> otherwise shows its children.
export default function Panel({ title, state, empty = "Nothing here yet.", isEmpty, children, className = "" }) {
  let content;
  if (!state) {
    content = <div className="skeleton"><span /><span /><span /></div>;
  } else if (state.notReady) {
    content = <p className="muted">Not connected yet — this feature is coming from the search service.</p>;
  } else if (state.error) {
    content = <p className="error">{state.error}</p>;
  } else if (isEmpty) {
    content = <p className="muted">{empty}</p>;
  } else {
    content = children;
  }
  return (
    <div className={`card panel ${className}`}>
      {title && <h3>{title}</h3>}
      {content}
    </div>
  );
}
