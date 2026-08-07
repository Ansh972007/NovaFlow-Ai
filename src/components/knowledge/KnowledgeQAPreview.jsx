"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { SearchIcon } from "@/components/workspace/WorkspaceIcons";
import {
  answerKnowledgeQuestion,
  retrieveKnowledge,
  searchKnowledgeChunks,
} from "@/lib/api/knowledge";

export default function KnowledgeQAPreview({ knowledgeId, readyCount = 0 }) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("retrieve");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [method, setMethod] = useState("");
  const [digest, setDigest] = useState("");
  const [citations, setCitations] = useState([]);
  const [embeddingAvailable, setEmbeddingAvailable] = useState(false);
  const [llmAvailable, setLlmAvailable] = useState(false);

  useEffect(() => {
    retrieveKnowledge(knowledgeId, "sample", { limit: 1 })
      .then((res) => {
        setEmbeddingAvailable(Boolean(res?.embedding_available));
        setLlmAvailable(Boolean(res?.llm_answer_available));
      })
      .catch(() => {
        setEmbeddingAvailable(false);
        setLlmAvailable(false);
      });
  }, [knowledgeId]);

  async function handleSubmit(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    setDigest("");
    setCitations([]);
    try {
      if (mode === "answer") {
        const res = await answerKnowledgeQuestion(knowledgeId, q, { limit: 5 });
        setDigest(res?.answer || "");
        setResults(res?.data || []);
        setTotal(res?.total || 0);
        setMethod(res?.method || "");
        setCitations(res?.citations || []);
        setEmbeddingAvailable(Boolean(res?.embedding_available));
        setLlmAvailable(Boolean(res?.llm_answer_available));
      } else if (mode === "retrieve") {
        const res = await retrieveKnowledge(knowledgeId, q, { limit: 5 });
        setDigest(res?.extractive_digest || "");
        setResults(res?.data || []);
        setTotal(res?.total || 0);
        setMethod(res?.method || "");
        setCitations(res?.citations || []);
        setEmbeddingAvailable(Boolean(res?.embedding_available));
        setLlmAvailable(Boolean(res?.llm_answer_available));
      } else {
        const res = await searchKnowledgeChunks(knowledgeId, q, { limit: 6 });
        setResults(res?.data || []);
        setTotal(res?.total || 0);
        setMethod(res?.method || res?.data?.[0]?.method || "");
        setEmbeddingAvailable(Boolean(res?.embedding_available));
        setLlmAvailable(Boolean(res?.llm_answer_available));
      }
    } catch (err) {
      setError(err.message || "Request failed");
      setResults([]);
      setTotal(0);
      setMethod("");
      setDigest("");
    } finally {
      setLoading(false);
    }
  }

  const disabled = readyCount === 0;
  const noLlmBadge = !embeddingAvailable || !llmAvailable;

  return (
    <div className="workspace-panel rounded-[1.75rem] p-6 sm:p-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="workspace-icon-tile h-11 w-11 shrink-0">
            <SearchIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="workspace-section-label">Q&A preview</p>
            <h2 className="mt-1 text-lg font-semibold tracking-tight">
              {mode === "retrieve" ? "Retrieve passages" : mode === "answer" ? "Ask your library" : "Keyword browse"}
            </h2>
            <p className="mt-1 text-sm text-neutral-500">
              {mode === "retrieve"
                ? "Top ranked passages with numbered citations — no LLM required."
                : mode === "answer"
                  ? "Hybrid retrieve + grounded answer when an LLM is configured."
                  : "Browse indexed chunks by keyword match."}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-full border border-neutral-200 bg-white p-0.5 text-[11px] font-semibold">
            <button
              type="button"
              onClick={() => setMode("retrieve")}
              className={`rounded-full px-3 py-1 ${mode === "retrieve" ? "bg-neutral-900 text-white" : "text-neutral-600"}`}
            >
              Retrieve
            </button>
            <button
              type="button"
              onClick={() => setMode("search")}
              className={`rounded-full px-3 py-1 ${mode === "search" ? "bg-neutral-900 text-white" : "text-neutral-600"}`}
            >
              Keyword browse
            </button>
            {llmAvailable && (
              <button
                type="button"
                onClick={() => setMode("answer")}
                className={`rounded-full px-3 py-1 ${mode === "answer" ? "bg-neutral-900 text-white" : "text-neutral-600"}`}
              >
                Answer
              </button>
            )}
          </div>
          {noLlmBadge && mode !== "answer" && (
            <span className="rounded-full border border-sky-200/80 bg-sky-50/90 px-3 py-1 text-[11px] font-semibold text-sky-800">
              No LLM — passages only
            </span>
          )}
          {disabled && (
            <span className="rounded-full border border-amber-200/80 bg-amber-50/90 px-3 py-1 text-[11px] font-semibold text-amber-800">
              Upload docs & wait for Ready
            </span>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={disabled || loading}
          placeholder="Ask a question about your documents…"
          className="flex-1 rounded-xl border border-neutral-200/80 bg-white/70 px-4 py-3 text-sm outline-none backdrop-blur-sm transition-colors focus:border-neutral-400 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || loading || !query.trim()}
          className="btn-primary shrink-0 !px-6 disabled:opacity-40"
        >
          {loading
            ? mode === "answer"
              ? "Answering…"
              : mode === "retrieve"
                ? "Retrieving…"
                : "Searching…"
            : mode === "answer"
              ? "Ask"
              : mode === "retrieve"
                ? "Retrieve"
                : "Search"}
        </button>
      </form>

      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      {digest && (
        <div className="mt-6 rounded-xl border border-emerald-200/70 bg-emerald-50/40 px-4 py-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
              {mode === "answer" && llmAvailable ? "Answer" : "Extractive digest"}
            </p>
            {method && (
              <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                {method}
              </span>
            )}
          </div>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-800">{digest}</p>
          {citations.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {citations.map((c) => (
                <span
                  key={c.n}
                  title={c.preview}
                  className="inline-flex max-w-[12rem] truncate rounded-full border border-emerald-200 bg-white px-2.5 py-0.5 text-[10px] font-semibold text-emerald-900"
                >
                  [{c.n}] {c.file_name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {results.length > 0 && (
        <div className="mt-6">
          <p className="mb-3 text-xs font-medium text-neutral-400">
            {total} matching chunk{total !== 1 ? "s" : ""}
            {method ? ` · ${method}` : ""}
          </p>
          <ul className="space-y-3">
            {results.map((chunk, i) => (
              <motion.li
                key={`${chunk.file_id}-${chunk.chunk_index ?? i}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="rounded-xl border border-white/60 bg-white/55 px-4 py-3.5 backdrop-blur-sm"
              >
                <div className="flex items-center justify-between gap-2 text-[11px] text-neutral-400">
                  <span className="truncate font-semibold text-neutral-800">
                    [{i + 1}] {chunk.file_name || chunk.source || `Document ${chunk.file_id}`}
                  </span>
                  <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5">
                    {chunk.method ? `${chunk.method} · ` : ""}
                    {chunk.score != null ? `score ${chunk.score}` : null}
                    {chunk.rrf != null ? ` · rrf ${chunk.rrf}` : ""}
                    {chunk.chunk_index != null ? ` · #${chunk.chunk_index}` : ""}
                  </span>
                </div>
                <p className="mt-2 line-clamp-4 text-sm leading-relaxed text-neutral-600">
                  {chunk.text || chunk.page_content || "—"}
                </p>
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {!loading && query.trim() && results.length === 0 && !error && !digest && (
        <p className="mt-6 text-center text-sm text-neutral-500">
          No matching chunks. Try different keywords.
        </p>
      )}
    </div>
  );
}
