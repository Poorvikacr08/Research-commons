import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiOptional } from "../api.js";
import ResultItem from "./ResultItem.jsx";

const TOPIC_VOCABULARY = [
  "artificial intelligence", "machine learning", "deep learning", "natural language processing",
  "computer vision", "data mining", "data science", "information retrieval", "knowledge graphs",
  "human-computer interaction", "cybersecurity", "computer networks", "cloud computing",
  "software engineering", "blockchain", "big data", "database systems", "recommendation systems",
];
const STOP_WORDS = new Set(["about", "after", "among", "analysis", "based", "case", "computer", "data", "from", "into", "method", "methods", "paper", "papers", "research", "study", "using", "with", "the", "and", "for"]);

function topicsFor(paper) {
  const text = `${paper.title || ""} ${paper.abstract || ""}`.toLowerCase();
  const matches = TOPIC_VOCABULARY.filter((topic) => text.includes(topic)).slice(0, 4);
  if (matches.length) return matches;
  const words = (paper.title || "").match(/[a-z][a-z-]{3,}/gi) || [];
  return [...new Set(words.map((word) => word.toLowerCase()).filter((word) => !STOP_WORDS.has(word)))].slice(0, 3);
}

export default function KnowledgeThread({ paper }) {
  const topics = useMemo(() => topicsFor(paper), [paper.id, paper.title, paper.abstract]);
  const [activeTopic, setActiveTopic] = useState(() => topics[0] || "research");
  const [searchState, setSearchState] = useState(null);

  useEffect(() => setActiveTopic(topics[0] || "research"), [paper.id, topics.join("|")]);
  useEffect(() => {
    let current = true;
    setSearchState(null);
    apiOptional(`/search?q=${encodeURIComponent(activeTopic)}`).then((result) => {
      if (current) setSearchState(result);
    });
    return () => { current = false; };
  }, [activeTopic]);

  const results = searchState?.data || {};
  const seen = new Set([String(paper.id)]);
  const relatedPapers = [...(results.external || []), ...(results.library || [])].filter((item) => {
    const key = String(item.id);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 3);
  const people = (results.people || []).slice(0, 3);
  const discussions = (results.posts || []).slice(0, 3);
  const authors = paper.authors?.split(",").map((name) => name.trim()).filter(Boolean).slice(0, 3) || [];
  const failed = Boolean(searchState?.error || searchState?.notReady);

  return (
    <section className="knowledge-thread" aria-labelledby="knowledge-thread-title">
      <div className="knowledge-thread-heading">
        <div>
          <p className="knowledge-eyebrow">CHANAKYA SCHOLARSPHERE · RESEARCH GRAPH</p>
          <h2 id="knowledge-thread-title">Knowledge thread</h2>
          <p>Follow this paper into the topics, people, and conversations around it.</p>
        </div>
        <span className="knowledge-thread-index" aria-hidden="true">01 — 04</span>
      </div>

      <div className="knowledge-thread-map">
        <div className="knowledge-node knowledge-origin">
          <span className="knowledge-node-kicker">START HERE</span>
          <strong>{paper.title}</strong>
          <span className="knowledge-node-meta">{[paper.year, paper.source].filter(Boolean).join(" · ") || "Research paper"}</span>
          {authors.length > 0 && <span className="knowledge-node-meta">{authors.join(" · ")}{paper.authors?.split(",").length > 3 ? " +" : ""}</span>}
        </div>

        <div className="knowledge-branch" aria-hidden="true"><span>THREADS THROUGH</span></div>

        <div className="knowledge-topic-node">
          <span className="knowledge-node-kicker">EXPLORE A TOPIC</span>
          <div className="knowledge-topic-list" aria-label="Topics found in this paper">
            {(topics.length ? topics : ["research"]).map((topic) => (
              <button key={topic} type="button" className={activeTopic === topic ? "knowledge-topic active" : "knowledge-topic"} aria-pressed={activeTopic === topic} onClick={() => setActiveTopic(topic)}>
                {topic}
              </button>
            ))}
          </div>
        </div>

        <div className="knowledge-branch knowledge-branch-down" aria-hidden="true"><span>DISCOVER</span></div>

        {failed ? (
          <div className="knowledge-thread-status" role="status">Related ScholarSphere connections are unavailable right now. You can still search this topic.</div>
        ) : (
          <div className="knowledge-destinations" aria-live="polite">
            <ThreadGroup number="02" title="Related papers" empty="No related papers surfaced yet." items={relatedPapers} loading={!searchState} />
            <ThreadGroup number="03" title="Researchers" empty="No matching researchers yet." items={people} loading={!searchState} />
            <ThreadGroup number="04" title="Discussions" empty="No matching discussions yet." items={discussions} loading={!searchState} />
          </div>
        )}
      </div>

      <div className="knowledge-thread-footer">
        <span>Exploring: <strong>{activeTopic || "research"}</strong></span>
        <Link to={`/search?q=${encodeURIComponent(activeTopic || "research")}`}>Search this thread <span aria-hidden="true">↗</span></Link>
      </div>
    </section>
  );
}

function ThreadGroup({ number, title, items, empty, loading }) {
  return (
    <section className="knowledge-group" aria-label={title}>
      <div className="knowledge-group-heading"><span>{number}</span><h3>{title}</h3></div>
      {loading ? <p className="knowledge-group-note">Tracing connections…</p> : items.length ? (
        <ul className="results knowledge-results">{items.map((item) => <ResultItem key={`${item.type}:${item.id}`} item={item} />)}</ul>
      ) : <p className="knowledge-group-note">{empty}</p>}
    </section>
  );
}
