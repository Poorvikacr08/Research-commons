// One paper in a list. Optional `children` (e.g. a note editor) show underneath.
import { Link } from "react-router-dom";
import SaveButton from "./SaveButton.jsx";

export default function PaperCard({ paper, onChange, children }) {
  return (
    <article className="card paper-card">
      <div className="row">
        <div className="post-main">
          <Link to={`/papers/${paper.id}`} className="post-title">{paper.title}</Link>
          <p className="muted">
            {[paper.authors, paper.year, paper.source].filter(Boolean).join(" · ")}
          </p>
          <p className="saved-by">
            📚 Saved by {paper.save_count} member{paper.save_count === 1 ? "" : "s"}
          </p>
        </div>
        <SaveButton paper={paper} onChange={onChange} />
      </div>
      {children}
    </article>
  );
}
