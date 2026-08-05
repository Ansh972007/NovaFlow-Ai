"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import WorkspaceTabs from "@/components/workspace/WorkspaceTabs";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import AnimatedCounter from "@/components/AnimatedCounter";
import { getUserInfo } from "@/lib/api/auth";
import { cloneMarketplaceWorkflow, listMarketplaceWorkflows, listWorkflowComments, postWorkflowComment, rateMarketplaceWorkflow } from "@/lib/api/marketplace";
import { createWorkflow } from "@/lib/api/workflows";

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

function StarRating({ value = 0, count = 0, onRate, disabled }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled || !onRate}
          onClick={() => onRate?.(star)}
          className={`text-base leading-none transition ${
            star <= Math.round(value) ? "text-amber-400" : "text-neutral-200"
          } ${onRate ? "hover:scale-110" : ""} disabled:cursor-default`}
          aria-label={`Rate ${star} stars`}
        >
          ★
        </button>
      ))}
      {count > 0 && <span className="ml-1 text-[11px] text-neutral-400">({count})</span>}
    </div>
  );
}

function WorkflowComments({ workflowId, count = 0, disabled }) {
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const rows = await listWorkflowComments(workflowId);
    setComments(Array.isArray(rows) ? rows : []);
  }

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      try {
        await load();
      } catch {
        setComments([]);
      }
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      const c = await postWorkflowComment(workflowId, text.trim());
      setComments((prev) => [c, ...prev]);
      setText("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 border-t border-neutral-100 pt-4">
      <button
        type="button"
        disabled={disabled}
        onClick={toggle}
        className="text-xs font-semibold text-neutral-600 hover:text-neutral-900"
      >
        {open ? "Hide comments" : `Comments (${count || comments.length || 0})`}
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          <form onSubmit={submit} className="flex gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Share feedback…"
              className="input-field flex-1 text-xs"
            />
            <button type="submit" disabled={busy} className="workspace-btn-ghost shrink-0 text-xs">
              Post
            </button>
          </form>
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
  const [user, setUser] = useState(null);
  const [items, setItems] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState("all");

  useEffect(() => {
    getUserInfo()
      .then((u) => {
        if (!u) {
          router.push("/login");
          return null;
        }
        setUser(u);
        return listMarketplaceWorkflows();
      })
      .then((res) => {
        if (!res) return;
        setItems(res?.items || []);
        setTemplates(res?.templates || []);
      })
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, [router]);

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
    setBusy(true);
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
    } finally {
      setBusy(false);
    }
  }

  async function handleClone(id) {
    setBusy(true);
    try {
      const w = await cloneMarketplaceWorkflow(id);
      if (w?.id) router.push(`/workflows/${w.id}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateFromTemplate(tpl) {
    setBusy(true);
    try {
      const wf = await createWorkflow({ name: tpl.name, templateId: tpl.id });
      if (wf?.id) router.push(`/workflows/${wf.id}`);
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return <WorkspaceLoading message="Loading marketplace…" />;
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
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />

      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="workspace-page-main mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">
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
                <Link href="/workflows" className="btn-secondary shrink-0">
                  Publish yours
                </Link>
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
                    <p className="text-sm text-neutral-500">Loading listings…</p>
                  ) : filteredItems.length === 0 ? (
                    <div className="workspace-empty rounded-2xl p-10 text-center">
                      <p className="font-medium">No public workflows yet</p>
                      <p className="mt-2 max-w-md mx-auto text-sm text-neutral-500">
                        Publish a workflow from the builder and mark it public to share it here.
                      </p>
                      <Link href="/workflows" className="btn-primary mt-6 inline-flex">
                        Open workflow studio
                      </Link>
                    </div>
                  ) : (
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
                              onRate={(score) => handleRate(w.id, score)}
                              disabled={busy}
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
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleClone(w.id)}
                            className="mt-5 flex w-full items-center justify-center gap-1 rounded-xl bg-neutral-900 py-2.5 text-xs font-semibold text-white transition hover:bg-neutral-800 disabled:opacity-60"
                          >
                            {busy ? "Cloning…" : "Clone to workspace"}
                            <span className="transition-transform group-hover:translate-x-0.5">→</span>
                          </button>
                          <WorkflowComments workflowId={w.id} count={w.comment_count} disabled={busy} />
                        </motion.article>
                      ))}
                    </div>
                  )}
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
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredTemplates.map((tpl, i) => (
                      <motion.button
                        key={tpl.id}
                        type="button"
                        disabled={busy}
                        initial={{ opacity: 0, y: 14 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.32 + i * 0.04, ease }}
                        onClick={() => handleCreateFromTemplate(tpl)}
                        className="workspace-card group rounded-2xl p-6 text-left transition-transform hover:scale-[1.01]"
                      >
                        <span className="text-2xl" aria-hidden>
                          {TEMPLATE_ICONS[tpl.id] || "⚡"}
                        </span>
                        <span className="mt-4 inline-block rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-bold uppercase text-violet-700">
                          Template
                        </span>
                        <h3 className="mt-3 text-lg font-semibold tracking-tight">{tpl.name}</h3>
                        <p className="mt-2 text-sm leading-relaxed text-neutral-500">{tpl.desc}</p>
                        <p className="mt-4 text-xs font-semibold text-neutral-900 opacity-0 transition-opacity group-hover:opacity-100">
                          Use template →
                        </p>
                      </motion.button>
                    ))}
                  </div>
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
                    Mark as public to list here
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
                        disabled={busy}
                        onClick={() => handleCreateFromTemplate(t)}
                        className="dashboard-recent-item block w-full rounded-xl px-3 py-2.5 text-left text-sm font-medium"
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
        </main>
      </div>
    </div>
  );
}
