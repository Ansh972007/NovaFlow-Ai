"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { WorkspaceStatCard, WorkspaceSkeletonGrid } from "@/components/workspace/WorkspaceTabs";
import { KnowledgeIcon } from "@/components/workspace/WorkspaceIcons";
import { getUserInfo } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import { useWorkspaceAccess } from "@/lib/auth/workspaceAccess";
import { ensureActiveWorkspace } from "@/lib/api/workspaces";
import {
  createKnowledge,
  deleteKnowledge,
  getEmbeddingModels,
  KB_STATUS_LABELS,
  listKnowledge,
} from "@/lib/api/knowledge";

const ease = [0.16, 1, 0.3, 1];

export default function KnowledgeListClient() {
  const router = useRouter();
  const { readOnly: workspaceReadOnly } = useWorkspaceAccess();
  const [user, setUser] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [model, setModel] = useState("");
  const [models, setModels] = useState([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [apiOffline, setApiOffline] = useState(false);
  const [searchName, setSearchName] = useState("");
  const [classification, setClassification] = useState("internal");

  const load = useCallback(async (nameFilter = searchName) => {
    setLoading(true);
    setLoadError("");
    setApiOffline(false);
    try {
      await ensureActiveWorkspace();
      const health = await checkBackendHealth();
      if (!health.ok) {
        setApiOffline(true);
        setLoadError(
          `NovaFlow API is not reachable (${health.apiUrl || "port 3001"}). Start the backend with docker compose up -d --build, then retry.`
        );
        setItems([]);
        setTotal(0);
        return;
      }
      const res = await listKnowledge({ pageSize: 50, name: nameFilter.trim() });
      setItems(res?.data || []);
      setTotal(res?.total || 0);
    } catch (err) {
      setItems([]);
      setTotal(0);
      setLoadError(err.message || "Failed to load knowledge libraries");
      if (
        String(err.message || "").includes("unavailable") ||
        String(err.message || "").includes("Cannot reach") ||
        String(err.message || "").includes("offline")
      ) {
        setApiOffline(true);
      }
    } finally {
      setLoading(false);
    }
  }, [searchName]);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        if (!u) {
          router.replace("/login");
          return;
        }
        try {
          await ensureActiveWorkspace();
        } catch {
          /* optional */
        }
        setUser(u);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    load();
    getEmbeddingModels()
      .then((res) => {
        const list = res?.models || [];
        setModels(list);
        if (list.length) setModel(String(list[0]));
      })
      .catch(() => setModels([]));
  }, [user, load]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      const kb = await createKnowledge({
        name: name.trim(),
        description: description.trim(),
        model: model || undefined,
        type: 0,
        classification,
      });
      setShowCreate(false);
      setName("");
      setDescription("");
      router.push(`/knowledge/${kb.id}`);
    } catch (err) {
      setError(err.message || "Failed to create knowledge base");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteKb(kb, e) {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete "${kb.name}"?`)) return;
    try {
      await deleteKnowledge(kb.id);
      load();
    } catch (err) {
      alert(err.message || "Failed to delete knowledge library");
    }
  }

  if (!user) {
    return null;
  }

  return (
    <>
    <WorkspacePageShell user={user} maxWidth="max-w-6xl">
          <WorkspaceHero
            eyebrow="Knowledge"
            title="Document"
            titleHighlight="libraries"
            description="Upload PDFs and docs to ground your AI assistants with accurate, retrieval-powered answers."
            badge={<span className="workspace-badge-live">RAG ready</span>}
            actions={
              !workspaceReadOnly ? (
                <button type="button" onClick={() => setShowCreate(true)} className="btn-primary shrink-0">
                  + New library
                </button>
              ) : null
            }
          >
            <div className="grid gap-3 sm:grid-cols-3">
              <WorkspaceStatCard label="Libraries" value={loading ? "…" : String(total)} hint="Document collections" />
              <WorkspaceStatCard
                label="Ready"
                value={loading ? "…" : String(items.filter((k) => k.status === "ready").length)}
                hint="Indexed for retrieval"
              />
              <WorkspaceStatCard label="Status" value={loading ? "…" : total ? "Active" : "Empty"} hint="Upload docs to get started" />
            </div>
          </WorkspaceHero>

          {loadError && (
            <WorkspaceAlert type="error" className="mt-6">
              {loadError}
              <button
                type="button"
                onClick={() => load()}
                className="ml-2 rounded-full border border-red-200 bg-white px-3 py-0.5 text-xs font-medium text-red-700 hover:bg-red-50"
              >
                Retry
              </button>
            </WorkspaceAlert>
          )}

          {apiOffline && (
            <WorkspaceAlert type="warn" className="mt-4">
              If you use Docker: run <code className="text-xs">docker compose up -d --build</code> from the
              project root, then open http://localhost:3000
            </WorkspaceAlert>
          )}

          {!loading && total > 0 && (
            <div className="mt-8">
              <input
                type="search"
                value={searchName}
                onChange={(e) => setSearchName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && load(searchName)}
                placeholder="Search libraries by name…"
                className="input-field w-full max-w-md"
              />
            </div>
          )}

          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.55, ease }}
            className="mt-10"
          >
            {!loading && total > 0 && (
              <p className="workspace-section-label mb-5">
                {total} librar{total !== 1 ? "ies" : "y"}
              </p>
            )}

            {loading ? (
              <WorkspaceSkeletonGrid count={6} />
            ) : items.length === 0 ? (
              <div className="workspace-empty rounded-[1.75rem] p-12 text-center sm:p-16">
                <div className="workspace-icon-tile mx-auto h-14 w-14">
                  <KnowledgeIcon className="h-6 w-6" />
                </div>
                <p className="mt-6 text-xl font-semibold tracking-tight">No knowledge bases yet</p>
                <p className="mx-auto mt-2 max-w-sm text-sm text-neutral-500">
                  Create a library, upload documents, and connect it to your assistants for RAG chat.
                </p>
                {!workspaceReadOnly && (
                  <button type="button" onClick={() => setShowCreate(true)} className="btn-primary mt-8">
                    Create your first library
                  </button>
                )}
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((kb, i) => {
                  const statusMeta = KB_STATUS_LABELS[kb.status] || KB_STATUS_LABELS.empty;
                  return (
                  <motion.div
                    key={kb.id}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.08 + i * 0.05, ease }}
                  >
                    <div className="workspace-card group relative block rounded-2xl p-6">
                      <div className="flex items-start justify-between gap-3">
                        <Link href={`/knowledge/${kb.id}`} className="workspace-icon-tile h-11 w-11 transition-transform duration-300 group-hover:scale-105">
                          <KnowledgeIcon className="h-5 w-5" />
                        </Link>
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase ${statusMeta.color}`}
                          >
                            {statusMeta.label}
                          </span>
                          {kb.classification && kb.classification !== "internal" && (
                            <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-700 ring-1 ring-violet-200/60">
                              {kb.classification}
                            </span>
                          )}
                          {!workspaceReadOnly && (
                            <button
                              type="button"
                              onClick={(e) => handleDeleteKb(kb, e)}
                              title="Delete library"
                              className="rounded-lg p-1.5 text-neutral-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                            >
                              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                      <Link href={`/knowledge/${kb.id}`} className="block">
                        <h2 className="mt-5 text-lg font-semibold tracking-tight group-hover:text-neutral-900">
                          {kb.name}
                        </h2>
                        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-neutral-500">
                          {kb.description || "No description"}
                        </p>
                        <p className="mt-5 flex items-center justify-between text-[11px] text-neutral-400">
                          <span>
                            {kb.ready_count || 0} ready · {kb.file_count || 0} docs
                          </span>
                          <span className="font-semibold text-neutral-700 opacity-0 transition-opacity group-hover:opacity-100">
                            Open →
                          </span>
                        </p>
                      </Link>
                    </div>
                  </motion.div>
                  );
                })}
              </div>
            )}
          </motion.section>
    </WorkspacePageShell>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4 backdrop-blur-md">
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="workspace-modal w-full max-w-md rounded-[1.5rem] p-7 sm:p-8"
          >
            <div className="flex items-start gap-4">
              <div className="workspace-icon-tile h-12 w-12 shrink-0">
                <KnowledgeIcon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-serif text-2xl tracking-tight">New knowledge base</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  Store documents for retrieval-augmented chat.
                </p>
              </div>
            </div>

            <form onSubmit={handleCreate} className="mt-7 space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium">Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-field w-full"
                  placeholder="Support docs"
                  required
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input-field w-full resize-none"
                  rows={2}
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Classification</label>
                <select
                  value={classification}
                  onChange={(e) => setClassification(e.target.value)}
                  className="input-field w-full"
                >
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="restricted">Restricted</option>
                </select>
              </div>
              {models.length > 0 && (
                <div>
                  <label className="mb-1.5 block text-sm font-medium">Embedding model</label>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="input-field w-full"
                  >
                    {models.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {error && (
                <p className="rounded-xl border border-red-200 bg-red-50/90 px-3 py-2 text-sm text-red-800">
                  {error}
                </p>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="workspace-btn-ghost flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="btn-primary flex-1 disabled:opacity-50"
                >
                  {creating ? "Creating…" : "Create library"}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </>
  );
}
