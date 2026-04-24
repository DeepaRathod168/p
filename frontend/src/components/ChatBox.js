import React, { useState, useRef, useEffect } from "react";
import { sendQuery, fetchHistory, clearHistory } from "../services/api";
import "./ChatBox.css";

/* ── Small sub-components ────────────────────────────────────────────────── */

function AgentStep({ icon, label, active, done }) {
  return (
    <div className={`agent-step ${active ? "active" : ""} ${done ? "done" : ""}`}>
      <span className="step-icon">{done ? "✅" : icon}</span>
      <span className="step-label">{label}</span>
      {active && <span className="spinner" />}
    </div>
  );
}

function InsightCard({ text, index }) {
  return (
    <div className="insight-card" style={{ animationDelay: `${index * 0.07}s` }}>
      <span className="insight-num">{String(index + 1).padStart(2, "0")}</span>
      <span className="insight-text">{text}</span>
    </div>
  );
}

function SourcePill({ url, index }) {
  const label = (() => {
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch {
      return url.slice(0, 40);
    }
  })();
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="source-pill"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      🔗 {label}
    </a>
  );
}

function HistoryItem({ item, onReuse }) {
  const [open, setOpen] = useState(false);
  const date = new Date(item.timestamp).toLocaleString();
  return (
    <div className="history-item">
      <button className="history-header" onClick={() => setOpen((o) => !o)}>
        <span className="history-query">{item.query}</span>
        <span className="history-meta">
          {date} · {item.duration_seconds}s
        </span>
        <span className="history-chevron">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="history-body">
          <p className="history-summary">{item.summary}</p>
          <button className="reuse-btn" onClick={() => onReuse(item.query)}>
            ↩ Re-run this query
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Main ChatBox component ──────────────────────────────────────────────── */

const AGENT_STEPS = [
  { icon: "🗂️", label: "RAG Context Retrieval" },
  { icon: "🔍", label: "Research Agent" },
  { icon: "📊", label: "Analysis Agent" },
  { icon: "✍️", label: "Summary Agent" },
];

export default function ChatBox() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState("");
  const [activeStep, setActiveStep] = useState(-1);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [copied, setCopied] = useState(false);

  const inputRef = useRef(null);
  const resultRef = useRef(null);

  // Load history on mount
  useEffect(() => {
    fetchHistory()
      .then(setHistory)
      .catch(() => {});
  }, []);

  const scrollToResult = () =>
    resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  const simulateSteps = (durationMs) => {
    const interval = Math.max(durationMs / AGENT_STEPS.length, 4000);
    let step = 0;
    setActiveStep(0);
    const timer = setInterval(() => {
      step += 1;
      if (step < AGENT_STEPS.length) {
        setActiveStep(step);
      } else {
        clearInterval(timer);
      }
    }, interval);
    return timer;
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setResponse(null);
    setActiveStep(0);

    const timer = simulateSteps(60_000);

    try {
      const data = await sendQuery(query.trim());
      clearInterval(timer);
      setActiveStep(AGENT_STEPS.length); // all done
      setResponse(data);
      // Refresh history
      fetchHistory().then(setHistory).catch(() => {});
      setTimeout(scrollToResult, 100);
    } catch (err) {
      clearInterval(timer);
      setActiveStep(-1);
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Something went wrong. Make sure the backend is running.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("Clear all history?")) return;
    await clearHistory().catch(() => {});
    setHistory([]);
  };

  const handleCopy = () => {
    if (!response) return;
    const text = [
      `Query: ${response.query}`,
      "",
      `Summary: ${response.summary}`,
      "",
      "Insights:",
      ...response.insights.map((ins, i) => `  ${i + 1}. ${ins}`),
      "",
      "Sources:",
      ...response.sources.map((s) => `  - ${s}`),
    ].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleReuse = (q) => {
    setQuery(q);
    setShowHistory(false);
    inputRef.current?.focus();
  };

  return (
    <div className="chatbox-root">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="chatbox-header">
        <div className="header-brand">
          <div className="brand-icon">⚡</div>
          <div>
            <h1 className="brand-name">ResearchAI</h1>
            <p className="brand-tagline">Multi-Agent · RAG · Real-time Insights</p>
          </div>
        </div>
        <div className="header-badges">
          <span className="badge badge-green">3 Agents</span>
          <span className="badge badge-blue">RAG</span>
          <span className="badge badge-purple">FastAPI</span>
          <button
            className="history-toggle-btn"
            onClick={() => setShowHistory((s) => !s)}
          >
            📚 History ({history.length})
          </button>
        </div>
      </header>

      {/* ── History drawer ──────────────────────────────────────────────── */}
      {showHistory && (
        <div className="history-drawer">
          <div className="history-drawer-header">
            <span>Research History</span>
            {history.length > 0 && (
              <button className="clear-history-btn" onClick={handleClear}>
                🗑️ Clear All
              </button>
            )}
          </div>
          {history.length === 0 ? (
            <p className="history-empty">No history yet. Run a query to get started!</p>
          ) : (
            history.map((item, i) => (
              <HistoryItem key={i} item={item} onReuse={handleReuse} />
            ))
          )}
        </div>
      )}

      {/* ── Query form ──────────────────────────────────────────────────── */}
      <form className="query-form" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <span className="input-icon">🔎</span>
          <input
            ref={inputRef}
            id="query-input"
            type="text"
            className="query-input"
            placeholder="Ask anything… e.g. How is AI transforming healthcare in 2026?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
            autoComplete="off"
          />
          {query && (
            <button
              type="button"
              className="clear-input-btn"
              onClick={() => setQuery("")}
              aria-label="Clear input"
            >
              ×
            </button>
          )}
        </div>
        <button
          id="submit-btn"
          type="submit"
          className={`submit-btn ${loading ? "loading" : ""}`}
          disabled={loading || !query.trim()}
        >
          {loading ? "Researching…" : "🚀 Research"}
        </button>
      </form>

      {/* ── Agent pipeline progress ─────────────────────────────────────── */}
      {loading && (
        <div className="pipeline-progress">
          <p className="pipeline-title">Agent Pipeline Running…</p>
          <div className="pipeline-steps">
            {AGENT_STEPS.map((step, i) => (
              <AgentStep
                key={i}
                icon={step.icon}
                label={step.label}
                active={activeStep === i}
                done={activeStep > i}
              />
            ))}
          </div>
          <p className="pipeline-note">This may take 1–3 minutes. Please wait.</p>
        </div>
      )}

      {/* ── Error ───────────────────────────────────────────────────────── */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* ── Result panel ────────────────────────────────────────────────── */}
      {response && (
        <div className="result-panel" ref={resultRef}>
          {/* Header row */}
          <div className="result-top">
            <div className="result-query-label">
              <span className="result-icon">📄</span>
              <span className="result-query-text">{response.query}</span>
            </div>
            <div className="result-meta">
              <span className="meta-pill">⏱ {response.duration_seconds}s</span>
              <span className="meta-pill">
                🕒 {new Date(response.timestamp).toLocaleTimeString()}
              </span>
              <button
                id="copy-btn"
                className={`copy-btn ${copied ? "copied" : ""}`}
                onClick={handleCopy}
              >
                {copied ? "✅ Copied!" : "📋 Copy"}
              </button>
            </div>
          </div>

          {/* Summary */}
          <section className="result-section">
            <h2 className="section-title">
              <span className="section-icon">💡</span> Executive Summary
            </h2>
            <p className="summary-text">{response.summary}</p>
          </section>

          {/* Insights */}
          {response.insights?.length > 0 && (
            <section className="result-section">
              <h2 className="section-title">
                <span className="section-icon">📊</span> Key Insights
              </h2>
              <div className="insights-grid">
                {response.insights.map((ins, i) => (
                  <InsightCard key={i} text={ins} index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Sources */}
          {response.sources?.length > 0 && (
            <section className="result-section">
              <h2 className="section-title">
                <span className="section-icon">🔗</span> Sources
              </h2>
              <div className="sources-list">
                {response.sources.map((src, i) => (
                  <SourcePill key={i} url={src} index={i} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* ── Empty state ─────────────────────────────────────────────────── */}
      {!loading && !response && !error && (
        <div className="empty-state">
          <div className="empty-icon">🤖</div>
          <p className="empty-title">Start a Research Query</p>
          <p className="empty-subtitle">
            Type any question above and let 3 AI agents search, analyse, and summarise
            the web — powered by RAG + CrewAI.
          </p>
          <div className="sample-queries">
            {[
              "Impact of AI agents on software jobs in 2026",
              "Latest breakthroughs in quantum computing",
              "How is CRISPR changing medicine?",
              "Best green energy investments in 2026",
            ].map((q) => (
              <button
                key={q}
                className="sample-query-btn"
                onClick={() => {
                  setQuery(q);
                  inputRef.current?.focus();
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
