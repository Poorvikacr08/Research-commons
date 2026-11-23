// Research assistant (F8): answer + numbered citations + the passages it used. From Member 3's POST /api/ask.
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiOptional } from "../api.js";

export default function Ask() {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setResult(null);
    setAsked(question.trim());
    setResult(await apiOptional("/ask", { method: "POST", body: { question: question.trim() } }));
    setBusy(false);
  }

  const data = result?.data;

  return (
    <section>
      <h1>Ask the research assistant</h1>
      <p className="muted">Answers come only from papers stored in Research Commons, with citations.</p>
      <form className="search-row big" onSubmit={submit}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. What methods are used to detect emerging research topics?" />
        <button type="submit" disabled={busy}>{busy ? "Thinking…" : "Ask"}</button>
      </form>

      {busy && <div className="card"><div className="skeleton"><span /><span /><span /></div></div>}
      {result?.notReady && <p className="card muted">The research assistant isn't connected yet.</p>}
      {result?.error && <p className="error">{result.error}</p>}

      {data && (
        <>
          <div className="card">
            <p className="muted">Q: {asked}</p>
            <p className="body answer">{data.answer}</p>
          </div>

          {data.citations?.length > 0 && (
            <div className="card">
              <h3>Sources</h3>
              <ol className="citations">
                {data.citations.map((c) => (
                  <li key={c.n} value={c.n}>
                    <Link to={`/papers/${c.paper_id}`}>{c.title}</Link>
                    {c.url && <> · <a href={c.url} target="_blank" rel="noreferrer">open ↗</a></>}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {data.passages?.length > 0 && (
            <details className="card">
              <summary>Retrieved passages ({data.passages.length})</summary>
              {data.passages.map((p, i) => (
                <blockquote key={i} className="passage">
                  <strong>[{p.n}]</strong> {p.text}
                  {p.score != null && <span className="muted"> · relevance {p.score.toFixed(2)}</span>}
                </blockquote>
              ))}
            </details>
          )}
        </>
      )}
    </section>
  );
}
