import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

const WELCOME = {
  id: "welcome",
  role: "assistant",
  content: "Hi! Ask me about the papers in ScholarSphere. I’ll find relevant passages and show you the sources.",
};

const SUGGESTIONS = [
  "What is data mining?",
  "How are research topics discovered?",
];

export default function ResearchChat() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([WELCOME]);
  const [busy, setBusy] = useState(false);
  const listRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    inputRef.current?.focus();
  }, [open, messages, busy]);

  async function sendQuestion(value = question) {
    const text = value.trim();
    if (!text || busy) return;

    setQuestion("");
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: text }]);
    setBusy(true);
    try {
      const result = await api("/ask", { method: "POST", body: { question: text } });
      setMessages((current) => [...current, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.answer || "I couldn’t find an answer in the current paper library.",
        citations: result.citations || [],
        passages: result.passages || [],
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: error.message || "I couldn’t reach the research assistant. Please try again.",
        failed: true,
      }]);
    } finally {
      setBusy(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    sendQuestion();
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendQuestion();
    }
  }

  return (
    <div className="research-chat-root">
      {open && (
        <section className="research-chat-panel" role="dialog" aria-label="ScholarSphere research chat">
          <header className="research-chat-header">
            <span className="research-chat-mark" aria-hidden="true">✦</span>
            <div>
              <strong>ScholarSphere AI</strong>
              <small>Research assistant · Paper library</small>
            </div>
            <button className="research-chat-close" type="button" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </header>

          <div className="research-chat-notice">Answers are based on papers in your library and include source links.</div>

          <div className="research-chat-messages" ref={listRef} aria-live="polite">
            {messages.map((message) => (
              <article className={`research-chat-message ${message.role}${message.failed ? " failed" : ""}`} key={message.id}>
                <p>{message.content}</p>
                {message.citations?.length > 0 && (
                  <div className="research-chat-sources">
                    <span className="research-chat-source-label">Sources</span>
                    {message.citations.map((citation) => (
                      <div className="research-chat-source" key={`${message.id}-${citation.n}`}>
                        <span>[{citation.n}]</span>
                        <Link to={`/papers/${citation.paper_id}`} onClick={() => setOpen(false)}>{citation.title}</Link>
                        {citation.url && <a href={citation.url} target="_blank" rel="noreferrer" aria-label={`Open ${citation.title} externally`}>↗</a>}
                      </div>
                    ))}
                  </div>
                )}
                {message.passages?.length > 0 && (
                  <details className="research-chat-passages">
                    <summary>View retrieved passages</summary>
                    {message.passages.map((passage) => <blockquote key={`${message.id}-p${passage.n}`}>[{passage.n}] {passage.text}</blockquote>)}
                  </details>
                )}
              </article>
            ))}
            {busy && <div className="research-chat-thinking" role="status"><span /> Searching papers…</div>}
          </div>

          {messages.length === 1 && (
            <div className="research-chat-suggestions" aria-label="Suggested questions">
              {SUGGESTIONS.map((suggestion) => (
                <button type="button" key={suggestion} onClick={() => sendQuestion(suggestion)} disabled={busy}>{suggestion}</button>
              ))}
            </div>
          )}

          <form className="research-chat-form" onSubmit={submit}>
            <textarea
              ref={inputRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about research…"
              rows={1}
              aria-label="Ask a research question"
              disabled={busy}
            />
            <button type="submit" aria-label="Send question" disabled={busy || !question.trim()}>
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 10h13M10 3l7 7-7 7" /></svg>
            </button>
          </form>
          <div className="research-chat-footnote">ScholarSphere can make mistakes. Verify answers with the cited papers.</div>
        </section>
      )}

      <button
        className={`research-chat-launcher${open ? " open" : ""}`}
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label={open ? "Close research chat" : "Open research chat"}
        aria-expanded={open}
      >
        {open ? <span aria-hidden="true">×</span> : <><span className="research-chat-launcher-icon" aria-hidden="true">✦</span><span>Ask ScholarSphere</span></>}
      </button>
    </div>
  );
}
