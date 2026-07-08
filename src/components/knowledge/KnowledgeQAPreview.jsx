"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { SearchIcon } from "@/components/workspace/WorkspaceIcons";
import { searchKnowledgeChunks } from "@/lib/api/knowledge";

export default function KnowledgeQAPreview({ knowledgeId, readyCount = 0 }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [method, setMethod] = useState("");

  async function handleSearch(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    try {
      const res = await searchKnowledgeChunks(knowledgeId, q, { limit: 6 });
      setResults(res?.data || []);
      setTotal(res?.total || 0);
      setMethod(res?.method || (res?.data?.[0]?.method) || "");
    } catch (err) {
      setError(err.message || "Search failed");
      setResults([]);
      setTotal(0);
      setMethod("");
    } finally {
      setLoading(false);
    }
  }

  const disabled = readyCount === 0;

  return (
    <div className="workspace-panel rounded-[1.75rem] p-6 sm:p-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="workspace-icon-tile h-11 w-11 shrink-0">
            <SearchIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="workspace-section-label">Q&A preview</p>
            <h2 className="mt-1 text-lg font-semibold tracking-tight">Test retrieval</h2>
            <p className="mt-1 text-sm text-neutral-500">
              Semantic search over indexed chunks (falls back to keywords without embeddings).
            </p>
          </div>
        </div>
        {disabled && (
          <span className="rounded-full border border-amber-200/80 bg-amber-50/90 px-3 py-1 text-[11px] font-semibold text-amber-800">
            Upload docs & wait for Ready
          </span>
        )}
      </div>

      <form onSubmit={handleSearch} className="mt-6 flex flex-col gap-2 sm:flex-row">
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
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
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
                    {chunk.file_name || chunk.source || `Document ${chunk.file_id}`}
                  </span>
                  <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5">
                    {chunk.score != null ? `score ${chunk.score}` : null}
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

      {!loading && query.trim() && results.length === 0 && !error && (
        <p className="mt-6 text-center text-sm text-neutral-500">
          No matching chunks. Try different keywords.
        </p>
      )}
    </div>
  );
}
