"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import WorkspaceEmpty from "@/components/workspace/WorkspaceEmpty";
import WorkspaceTabs from "@/components/workspace/WorkspaceTabs";
import { WorkspaceSkeletonGrid } from "@/components/workspace/WorkspaceTabs";
import AnimatedCounter from "@/components/AnimatedCounter";
import { useWorkspaceAccess } from "@/lib/auth/workspaceAccess";
import { getUserInfo } from "@/lib/api/auth";
import { ensureActiveWorkspace } from "@/lib/api/workspaces";
import {
  cloneMarketplaceWorkflow,
  listMarketplaceWorkflows,
  listWorkflowComments,
  postWorkflowComment,
  rateMarketplaceWorkflow,
  setWorkflowPublic,
} from "@/lib/api/marketplace";
import { createWorkflow, getWorkflowsPage } from "@/lib/api/workflows";

const ease = [0.16, 1, 0.3, 1];

const TEMPLATE_ICONS = {
  rag: "📚",
  support: "🎫",
  research: "🔬",
  enrich: "✨",
  agent_loop: "🤖",
  batch: "📦",
};

function nodeCount(graph) {
  return graph?.nodes?.length || 0;
}

function StarRating({ value = 0, count = 0, onRate, disabled, busy }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled || busy || !onRate}
          onClick={() => onRate?.(star)}
          className={`text-base leading-none transition ${
            star <= Math.round(value) ? "text-amber-400" : "text-neutral-200"
          } ${onRate ? "hover:scale-110" : ""} disabled:cursor-default disabled:opacity-60`}
          aria-label={`Rate ${star} stars`}
        >
          ★
        </button>
      ))}
      {count > 0 && <span className="ml-1 text-[11px] text-neutral-400">({count})</span>}
      {busy ? <span className="ml-2 text-[10px] text-neutral-400">Saving…</span> : null}
    </div>
  );
}

function WorkflowComments({ workflowId, count = 0, readOnly }) {
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    const rows = await listWorkflowComments(workflowId);
    setComments(Array.isArray(rows) ? rows : []);
  }

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      try {
        await load();
      } catch (err) {
        setError(err.message || "Failed to load comments");
        setComments([]);
      }
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (!text.trim() || readOnly) return;
    setBusy(true);
    setError("");
    try {
      const c = await postWorkflowComment(workflowId, text.trim());
      setComments((prev) => [c, ...prev]);
      setText("");
    } catch (err) {
      setError(err.message || "Failed to post comment");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 border-t border-neutral-100 pt-4">
      <button
        type="button"
        onClick={toggle}
        className="text-xs font-semibold text-neutral-600 hover:text-neutral-900"
      >
        {open ? "Hide comments" : `Comments (${count || comments.length || 0})`}
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          {error ? <p className="text-xs text-red-600">{error}</p> : null}
          {!readOnly ? (
            <form onSubmit={submit} className="flex gap-2">
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Share feedback…"
                className="input-field flex-1 text-xs"
                disabled={busy}
              />
              <button type="submit" disabled={busy} className="workspace-btn-ghost shrink-0 text-xs">
                Post
              </button>
            </form>
          ) : (
            <p className="text-xs text-neutral-400">Viewer access — commenting disabled.</p>
          )}
          <ul className="max-h-40 space-y-2 overflow-y-auto">
            {comments.length === 0 ? (
              <li className="text-xs text-neutral-400">No comments yet.</li>
            ) : (
              comments.map((c) => (
                <li key={c.id} className="rounded-lg bg-neutral-50 px-3 py-2 text-xs">
                  <p className="font-semibold text-neutral-700">{c.user_name}</p>
                  <p className="mt-0.5 text-neutral-600">{c.body}</p>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function MarketplaceClient() {
  const router = useRouter();
  const { readOnly: workspaceReadOnly } = useWorkspaceAccess();
  const [user, setUser] = useState(null);
  const [items, setItems] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [cloneBusyId, setCloneBusyId] = useState(null);
  const [rateBusyId, setRateBusyId] = useState(null);
  const [templateBusyId, setTemplateBusyId] = useState(null);
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState("all");
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [myWorkflows, setMyWorkflows] = useState([]);
  const [loadingMyWorkflows, setLoadingMyWorkflows] = useState(false);
  const [publishBusyId, setPublishBusyId] = useState(null);

  const readOnly = workspaceReadOnly || user?.role === "viewer";

  async function openPublishModal() {
    setShowPublishModal(true);
    setLoadingMyWorkflows(true);
    try {
      const res = await getWorkflowsPage({ limit: 100 });
      setMyWorkflows(res?.data || []);
    } catch {
      setMyWorkflows([]);
    } finally {
      setLoadingMyWorkflows(false);
    }
  }

  async function handlePublishToMarketplace(workflowId, currentPublic) {
    setPublishBusyId(workflowId);
    setError("");
    setSuccess("");
    try {
      const next = !currentPublic;
      await setWorkflowPublic(workflowId, next);
      setMyWorkflows((prev) =>
        prev.map((w) => (w.id === workflowId ? { ...w, is_public: next ? 1 : 0 } : w))
      );
      setSuccess(next ? "Workflow published to community marketplace!" : "Workflow unpublished from marketplace.");
      await load();
    } catch (err) {
      setError(err.message || "Failed to update marketplace status");
    } finally {
      setPublishBusyId(null);
    }
  }

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const res = await listMarketplaceWorkflows();
      setItems(res?.items || []);
      setTemplates(res?.templates || []);
    } catch (err) {
      setItems([]);
      setTemplates([]);
      setLoadError(err.message || "Failed to load marketplace");
    } finally {
      setLoading(false);
    }
  }, []);

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
      .catch(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const filteredItems = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (w) => w.name?.toLowerCase().includes(q) || w.desc?.toLowerCase().includes(q)
    );
  }, [items, query]);

  const filteredTemplates = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return templates;
    return templates.filter(
      (t) => t.name?.toLowerCase().includes(q) || t.desc?.toLowerCase().includes(q)
    );
  }, [templates, query]);

  async function handleRate(workflowId, score) {
    if (readOnly) return;
    setRateBusyId(workflowId);
    setError("");
    setSuccess("");
    try {
      const res = await rateMarketplaceWorkflow(workflowId, { score });
      setItems((prev) =>
        prev.map((w) =>
          w.id === workflowId
            ? {
                ...w,
                avg_rating: res?.avg_rating ?? score,
                rating_count: res?.rating_count ?? w.rating_count,
                user_rating: score,
              }
            : w
        )
      );
      setSuccess("Rating saved.");
    } catch (err) {
      setError(err.message || "Rating failed");
    } finally {
      setRateBusyId(null);
    }
  }

  async function handleClone(id) {
    if (readOnly) return;
    setCloneBusyId(id);
    setError("");
    setSuccess("");
    try {
      const w = await cloneMarketplaceWorkflow(id);
      if (w?.id) router.push(`/workflows/${w.id}`);
    } catch (err) {
      setError(err.message || "Clone failed");
    } finally {
      setCloneBusyId(null);
    }
  }

  async function handleCreateFromTemplate(tpl) {
    if (readOnly) return;
    setTemplateBusyId(tpl.id);
    setError("");
    setSuccess("");
    try {
      const wf = await createWorkflow({ name: tpl.name, templateId: tpl.id });
      if (wf?.id) router.push(`/workflows/${wf.id}`);
    } catch (err) {
      setError(err.message || "Failed to create from template");
    } finally {
      setTemplateBusyId(null);
    }
  }

  const showCommunity = tab === "all" || tab === "community";
  const showTemplates = tab === "all" || tab === "templates";

  const visibleCount =
    tab === "templates"
      ? filteredTemplates.length
      : tab === "community"
        ? filteredItems.length
        : filteredItems.length + filteredTemplates.length;

  return (
    <WorkspacePageShell user={user} loading={!user || loading} loadingMessage="Loading marketplace…" maxWidth="max-w-6xl">
      <WorkspaceHero
        eyebrow="Discover & share"
        title="Workflow"
        titleHighlight="marketplace"
        description="Clone community pipelines or start from battle-tested templates — same polish as your dashboard, zero setup friction."
        badge={
          <span className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/80 px-4 py-1.5 text-[11px] font-semibold tracking-[0.14em] uppercase backdrop-blur-md">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-500 opacity-40" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-violet-500" />
            </span>
            <span className="text-violet-700">Community templates</span>
          </span>
        }
        actions={
          <>
            <Link href="/workflows" className="btn-primary shrink-0">
              My workflows
            </Link>
            <button
              type="button"
              onClick={openPublishModal}
              className="btn-secondary shrink-0 flex items-center gap-1.5"
            >
              <span>🚀</span>
              <span>Publish yours</span>
            </button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { value: String(items.length), label: "Public workflows", hint: "Shared by teams" },
            { value: String(templates.length), label: "Built-in templates", hint: "Ready to customize" },
            { value: String(visibleCount), label: "Showing now", hint: query ? "Search results" : "All listings" },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.06, ease }}
              className="workspace-stat rounded-2xl p-5"
            >
              <p className="text-3xl font-semibold tabular-nums tracking-tight sm:text-4xl">
                <AnimatedCounter value={stat.value} />
              </p>
              <p className="mt-1.5 text-sm font-semibold text-neutral-900">{stat.label}</p>
              <p className="mt-0.5 text-xs text-neutral-400">{stat.hint}</p>
            </motion.div>
          ))}
        </div>
      </WorkspaceHero>

      {readOnly && (
        <WorkspaceAlert type="warn" className="mt-4">
          Viewer access — you can browse the marketplace but cannot clone, rate, or comment.
        </WorkspaceAlert>
      )}

      {loadError ? (
        <WorkspaceAlert type="error" className="mt-4">
          {loadError}
          <button
            type="button"
            onClick={() => load()}
            className="ml-2 rounded-full border border-red-200 bg-white px-3 py-0.5 text-xs font-medium text-red-700 hover:bg-red-50"
          >
            Retry
          </button>
        </WorkspaceAlert>
      ) : null}

      {error ? <WorkspaceAlert type="error" className="mt-4">{error}</WorkspaceAlert> : null}
      {success ? <WorkspaceAlert type="success" className="mt-4">{success}</WorkspaceAlert> : null}

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, ease }}
        className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <WorkspaceTabs
          tabs={[
            { id: "all", label: "All" },
            { id: "community", label: "Community", count: items.length },
            { id: "templates", label: "Templates", count: templates.length },
          ]}
          active={tab}
          onChange={setTab}
        />
        <div className="workspace-search-wrap w-full sm:max-w-xs">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3-3" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search workflows & templates…"
            className="workspace-search-input"
          />
        </div>
      </motion.div>

      <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="space-y-10">
          {showCommunity && (
            <motion.section
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.24, ease }}
            >
              <div className="mb-5 flex items-end justify-between">
                <div>
                  <p className="workspace-section-label">Community</p>
                  <h2 className="mt-1 text-xl font-semibold tracking-tight">Public workflows</h2>
                </div>
              </div>

              {loading ? (
                <WorkspaceSkeletonGrid count={4} columns="sm:grid-cols-2" />
              ) : filteredItems.length === 0 && !loadError ? (
                <WorkspaceEmpty
                  title="No public workflows yet"
                  description="Publish a workflow from the builder and toggle Public in the header to list it here."
                  actionLabel="Open workflow studio"
                  actionHref="/workflows"
                  icon="◇"
                />
              ) : filteredItems.length > 0 ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  {filteredItems.map((w, i) => (
                    <motion.article
                      key={w.id}
                      initial={{ opacity: 0, y: 18 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.26 + i * 0.05, ease }}
                      className="workspace-card group rounded-2xl p-6"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="workspace-icon-tile h-11 w-11 shrink-0">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                            <circle cx="6" cy="6" r="2" />
                            <circle cx="18" cy="6" r="2" />
                            <circle cx="12" cy="18" r="2" />
                            <path d="M8 6h8M7.5 7.5L10.5 16M16.5 7.5L13.5 16" />
                          </svg>
                        </div>
                        {w.from_workspace && (
                          <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-bold uppercase text-sky-700">
                            External
                          </span>
                        )}
                      </div>
                      <h3 className="mt-5 text-lg font-semibold tracking-tight group-hover:text-neutral-700">
                        {w.name}
                      </h3>
                      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-neutral-500">
                        {w.desc || "No description provided."}
                      </p>
                      <div className="mt-3">
                        <StarRating
                          value={w.user_rating || w.avg_rating || 0}
                          count={w.rating_count || 0}
                          onRate={readOnly ? undefined : (score) => handleRate(w.id, score)}
                          disabled={readOnly}
                          busy={rateBusyId === w.id}
                        />
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-neutral-400">
                        <span className="rounded-full bg-neutral-100 px-2 py-0.5 font-medium">
                          {nodeCount(w.graph)} nodes
                        </span>
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
                          Published
                        </span>
                      </div>
                      {!readOnly ? (
                        <button
                          type="button"
                          disabled={cloneBusyId === w.id}
                          onClick={() => handleClone(w.id)}
                          className="mt-5 flex w-full items-center justify-center gap-1 rounded-xl bg-neutral-900 py-2.5 text-xs font-semibold text-white transition hover:bg-neutral-800 disabled:opacity-60"
                        >
                          {cloneBusyId === w.id ? "Cloning…" : "Clone to workspace"}
                          <span className="transition-transform group-hover:translate-x-0.5">→</span>
                        </button>
                      ) : null}
                      <WorkflowComments workflowId={w.id} count={w.comment_count} readOnly={readOnly} />
                    </motion.article>
                  ))}
                </div>
              ) : null}
            </motion.section>
          )}

          {showTemplates && (
            <motion.section
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, ease }}
            >
              <div className="mb-5">
                <p className="workspace-section-label">Official</p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight">Starter templates</h2>
              </div>
              {filteredTemplates.length === 0 && !loading && !loadError ? (
                <p className="text-sm text-neutral-500">No templates match your search.</p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredTemplates.map((tpl, i) => (
                    <motion.button
                      key={tpl.id}
                      type="button"
                      disabled={readOnly || templateBusyId === tpl.id}
                      initial={{ opacity: 0, y: 14 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.32 + i * 0.04, ease }}
                      onClick={() => handleCreateFromTemplate(tpl)}
                      className="workspace-card group rounded-2xl p-6 text-left transition-transform hover:scale-[1.01] disabled:opacity-60"
                    >
                      <span className="text-2xl" aria-hidden>
                        {TEMPLATE_ICONS[tpl.id] || "⚡"}
                      </span>
                      <span className="mt-4 inline-block rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-bold uppercase text-violet-700">
                        Template
                      </span>
                      <h3 className="mt-3 text-lg font-semibold tracking-tight">{tpl.name}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-neutral-500">{tpl.desc}</p>
                      <p className="mt-4 text-xs font-semibold text-neutral-900">
                        {templateBusyId === tpl.id ? "Creating…" : "Use template →"}
                      </p>
                    </motion.button>
                  ))}
                </div>
              )}
            </motion.section>
          )}
        </div>

        <aside className="space-y-6">
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.28, ease }}
            className="workspace-panel rounded-2xl p-5"
          >
            <h2 className="text-sm font-semibold tracking-tight">How sharing works</h2>
            <ol className="mt-4 space-y-3 text-sm text-neutral-600">
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-[11px] font-bold text-white">1</span>
                Build a workflow in the studio
              </li>
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-[11px] font-bold text-white">2</span>
                Publish it live
              </li>
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-[11px] font-bold text-white">3</span>
                Toggle <strong>Public</strong> in the builder header
              </li>
            </ol>
            <Link href="/workflows" className="mt-5 inline-flex text-xs font-semibold text-neutral-800 hover:underline">
              Go to workflows →
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.34, ease }}
            className="workspace-panel rounded-2xl p-5"
          >
            <h2 className="text-sm font-semibold tracking-tight">Popular picks</h2>
            <ul className="mt-4 space-y-2">
              {(templates.slice(0, 4).length ? templates.slice(0, 4) : [{ id: "rag", name: "RAG Q&A" }]).map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    disabled={readOnly || templateBusyId === t.id}
                    onClick={() => handleCreateFromTemplate(t)}
                    className="dashboard-recent-item block w-full rounded-xl px-3 py-2.5 text-left text-sm font-medium disabled:opacity-50"
                  >
                    {TEMPLATE_ICONS[t.id] || "⚡"} {t.name}
                  </button>
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4, ease }}
            className="rounded-2xl border border-dashed border-black/10 bg-white/40 p-5 text-sm text-neutral-500"
          >
            <p className="font-semibold text-neutral-800">Need custom workflows?</p>
            <p className="mt-1">Combine marketplace presets with custom automated pipelines.</p>
            <Link href="/workflows" className="mt-3 inline-block text-xs font-semibold hover:underline">
              Open workflows →
            </Link>
          </motion.div>
        </aside>
      </div>

      {showPublishModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-neutral-200 bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-4">
              <div>
                <h3 className="text-base font-semibold text-neutral-900">Publish to Community Marketplace</h3>
                <p className="text-xs text-neutral-500">
                  Share your workflows so every user and team can discover, rate, and clone them.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowPublishModal(false)}
                className="rounded-full p-2 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 max-h-[60vh] overflow-y-auto space-y-3 pr-1">
              {loadingMyWorkflows ? (
                <p className="py-8 text-center text-xs text-neutral-400">Loading your workflows…</p>
              ) : myWorkflows.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-sm font-medium text-neutral-700">No workflows found in this workspace.</p>
                  <Link href="/workflows" className="mt-2 inline-block text-xs font-semibold text-indigo-600 hover:underline">
                    Create a workflow first →
                  </Link>
                </div>
              ) : (
                myWorkflows.map((wf) => (
                  <div
                    key={wf.id}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-neutral-100 bg-neutral-50/70 p-3.5 transition hover:border-neutral-200 hover:bg-white"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-semibold text-neutral-900">{wf.name}</p>
                        {wf.is_public === 1 && (
                          <span className="shrink-0 rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
                            Public
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 truncate text-xs text-neutral-500">
                        {wf.desc || "No description provided"}
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled={publishBusyId === wf.id || readOnly}
                      onClick={() => handlePublishToMarketplace(wf.id, wf.is_public === 1)}
                      className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition disabled:opacity-50 ${
                        wf.is_public === 1
                          ? "border border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50"
                          : "bg-neutral-900 text-white hover:bg-black"
                      }`}
                    >
                      {publishBusyId === wf.id
                        ? "Saving…"
                        : wf.is_public === 1
                          ? "Unpublish"
                          : "Publish ➔"}
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="mt-6 flex justify-end border-t border-neutral-100 pt-4">
              <button
                type="button"
                onClick={() => setShowPublishModal(false)}
                className="btn-secondary !py-2 !text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </WorkspacePageShell>
  );
}
