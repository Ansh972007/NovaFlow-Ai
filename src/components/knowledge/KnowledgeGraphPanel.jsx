"use client";

import { useCallback, useEffect, useState } from "react";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import {
  buildKnowledgeGraphForFile,
  getKnowledgeEntityGraph,
  searchKnowledgeEntities,
} from "@/lib/api/kos";

export default function KnowledgeGraphPanel({ files, writeable }) {
  const [query, setQuery] = useState("");
  const [entities, setEntities] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [buildBusy, setBuildBusy] = useState("");

  const loadEntities = useCallback(async (searchQuery = query) => {
    setLoading(true);
    setError("");
    try {
      const res = await searchKnowledgeEntities({ q: searchQuery.trim(), limit: 40 });
      const rows = Array.isArray(res) ? res : res?.data || res?.items || [];
      setEntities(rows);
      if (!selectedId && rows[0]?.id) setSelectedId(rows[0].id);
    } catch (err) {
      setError(err.message || "Failed to load entities");
    } finally {
      setLoading(false);
    }
  }, [query, selectedId]);

  useEffect(() => {
    loadEntities("");
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setGraph({ nodes: [], edges: [] });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await getKnowledgeEntityGraph(selectedId);
        if (!cancelled) setGraph(res || { nodes: [], edges: [] });
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load graph");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function handleBuild(fileId) {
    if (!writeable || !fileId) return;
    setBuildBusy(String(fileId));
    setError("");
    try {
      await buildKnowledgeGraphForFile(fileId);
      await loadEntities();
    } catch (err) {
      setError(err.message || "Graph build failed");
    } finally {
      setBuildBusy("");
    }
  }

  const readyFiles = (files || []).filter((f) => f.status === 2).slice(0, 8);

  return (
    <section className="workspace-card mt-6 rounded-2xl p-5">
      <h2 className="text-sm font-semibold text-neutral-900">Knowledge graph</h2>
      <p className="mt-1 text-xs text-neutral-500">
        Explore entities extracted from documents and their relationships.
      </p>

      {error && <WorkspaceAlert type="error" className="mt-3">{error}</WorkspaceAlert>}

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <input
          className="input-field min-w-0 flex-1 text-sm"
          placeholder="Search entities…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="button" className="btn-secondary text-xs" onClick={() => loadEntities()} disabled={loading}>
          {loading ? "Loading…" : "Search"}
        </button>
      </div>

      {readyFiles.length > 0 && writeable && (
        <div className="mt-3 flex flex-wrap gap-2">
          {readyFiles.map((f) => (
            <button
              key={f.id}
              type="button"
              className="rounded-full bg-neutral-100 px-3 py-1 text-[10px] font-medium text-neutral-700 ring-1 ring-black/5"
              disabled={buildBusy === String(f.id)}
              onClick={() => handleBuild(f.id)}
            >
              {buildBusy === String(f.id) ? "Building…" : `Build graph: ${f.file_name || f.id}`}
            </button>
          ))}
        </div>
      )}

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <ul className="max-h-48 space-y-1 overflow-y-auto text-xs">
          {entities.length === 0 && !loading && (
            <li className="text-neutral-500">No entities yet — upload docs and build graph.</li>
          )}
          {entities.map((ent) => (
            <li key={ent.id}>
              <button
                type="button"
                className={`w-full rounded-lg px-2 py-1.5 text-left ${
                  selectedId === ent.id ? "bg-violet-50 font-semibold text-violet-900" : "hover:bg-neutral-50"
                }`}
                onClick={() => setSelectedId(ent.id)}
              >
                <span className="text-[10px] uppercase text-neutral-400">{ent.type}</span>
                <span className="ml-2">{ent.name}</span>
              </button>
            </li>
          ))}
        </ul>

        <div className="rounded-xl bg-neutral-50 p-3 text-xs ring-1 ring-black/5">
          <p className="font-semibold text-neutral-800">
            {graph.nodes?.length || 0} nodes · {graph.edges?.length || 0} edges
          </p>
          <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">
            {(graph.edges || []).map((edge) => (
              <li key={edge.id} className="text-neutral-600">
                {edge.source} → {edge.target}
                {edge.type ? ` (${edge.type})` : ""}
              </li>
            ))}
            {!graph.edges?.length && (
              <li className="text-neutral-500">Select an entity to view local relationships.</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
