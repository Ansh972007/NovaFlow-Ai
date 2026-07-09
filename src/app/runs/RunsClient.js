"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import AnimatedCounter from "@/components/AnimatedCounter";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import WorkspaceEmpty from "@/components/workspace/WorkspaceEmpty";
import { getUserInfo } from "@/lib/api/auth";
import { getWorkflowRun, getWorkflowsPage, listWorkspaceRuns } from "@/lib/api/workflows";

const ease = [0.16, 1, 0.3, 1];

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatDuration(ms) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

function isRunError(run) {
  return run?.status === 2 || run?.status_label === "error";
}

function runStatusLabel(run) {
  if (run?.status_label) return run.status_label;
  return isRunError(run) ? "error" : "completed";
}

function RunStatusBadge({ run, large = false }) {
  const err = isRunError(run);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-bold tracking-wide uppercase ${
        large ? "px-3 py-1 text-[11px]" : "px-2 py-0.5 text-[10px]"
      } ${err ? "border-black bg-white text-black" : "border-black bg-black text-white"}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${err ? "bg-black" : "bg-white"}`} />
      {runStatusLabel(run)}
    </span>
  );
}

function exportRunJson(detail) {
  const blob = new Blob([JSON.stringify(detail, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `run-${detail.id}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportRunMd(detail) {
  const lines = [
    `# Run #${detail.id} — ${detail.workflow_name || ""}`,
    "",
    `- Status: ${detail.status_label || detail.status || "—"}`,
    `- Duration: ${detail.duration_ms || 0}ms`,
    `- Created: ${detail.create_time || "—"}`,
    `- Workflow ID: ${detail.workflow_id || "—"}`,
    "",
    "## Input",
    "",
    "```",
    detail.input || "—",
    "```",
    "",
    "## Output",
    "",
    "```",
    detail.output || "—",
    "```",
    "",
    "## Steps",
    "",
  ];
  (detail.steps || []).forEach((step, i) => {
    const label = step.type || step.node_type || "step";
    const nid = step.node_id || step.id || "";
    lines.push(`### ${i + 1}. ${label}${nid ? ` (\`${nid}\`)` : ""} — ${step.status || "—"}`);
    lines.push("");
    if (step.iterations != null) lines.push(`- Iterations: ${step.iterations}`);
    if (step.matched != null) lines.push(`- Matched: ${step.matched}`);
    if (step.message) lines.push(`- Message: ${step.message}`);
    lines.push("");
    lines.push("```");
    lines.push(step.output || step.message || "—");
    lines.push("```");
    lines.push("");
  });
  const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `run-${detail.id}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportRunCsv(detail) {
  const rows = [["step", "node_id", "type", "status", "iterations", "output"]];
  (detail.steps || []).forEach((step, i) => {
    rows.push([
      String(i + 1),
      step.node_id || step.id || "",
      step.type || step.node_type || "",
      step.status || "",
      step.iterations != null ? String(step.iterations) : "",
      String(step.output || step.message || "").replace(/\r?\n/g, " "),
    ]);
  });
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `run-${detail.id}-steps.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function StepTimeline({ steps }) {
  if (!steps?.length) {
    return <p className="text-xs text-neutral-400">No step payload for this run.</p>;
  }

  return (
    <ol className="relative space-y-0">
      {steps.map((step, i) => {
        const label = step.type || step.node_type || "step";
        const ok = step.status === "ok";
        const err = step.status === "error";
        return (
          <motion.li
            key={`${label}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04, duration: 0.35, ease }}
            className="relative flex gap-3 pb-5 last:pb-0"
          >
            {i < steps.length - 1 && (
              <span className="absolute top-7 left-[11px] h-[calc(100%-12px)] w-px bg-neutral-200" />
            )}
            <span
              className={`relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-[9px] font-bold ${
                ok ? "border-black bg-black text-white" : err ? "border-black bg-white text-black" : "border-neutral-300 bg-neutral-50 text-neutral-500"
              }`}
            >
              {i + 1}
            </span>
            <div className="min-w-0 flex-1 rounded-xl border border-black/[0.06] bg-neutral-50/80 px-3 py-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-[11px] font-semibold text-neutral-900">{label}</p>
                <span className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">{step.status || "—"}</span>
              </div>
              {(step.node_id || step.id) && (
                <p className="mt-0.5 font-mono text-[10px] text-neutral-400">{step.node_id || step.id}</p>
              )}
              <p className="mt-2 line-clamp-4 whitespace-pre-wrap text-[11px] leading-relaxed text-neutral-600">
                {step.output || step.message || "—"}
              </p>
            </div>
          </motion.li>
        );
      })}
    </ol>
  );
}

function RunCard({ run, active, onSelect, index }) {
  const err = isRunError(run);
  return (
    <motion.li
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.4, ease }}
      whileHover={{ x: 2 }}
    >
      <button
        type="button"
        onClick={() => onSelect(run.id)}
        className={`noise group relative w-full overflow-hidden rounded-2xl border text-left transition-all duration-300 ${
          active
            ? "border-black bg-white shadow-[0_12px_40px_-16px_rgba(0,0,0,0.25)]"
            : "border-neutral-200 bg-white hover:border-neutral-400 hover:shadow-md hover:shadow-black/5"
        }`}
      >
        <span
          className={`absolute top-0 left-0 h-full w-1 transition-colors ${err ? "bg-neutral-400" : "bg-black"} ${active ? "w-1.5" : ""}`}
        />
        <div className="px-4 py-3.5 pl-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href={`/workflows/${run.workflow_id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="font-semibold text-neutral-900 hover:underline"
                >
                  {run.workflow_name || run.workflow_id}
                </Link>
                <span className="font-mono text-[10px] text-neutral-400">#{run.id}</span>
              </div>
              <p className="mt-1.5 line-clamp-1 text-sm text-neutral-600">{run.input || "No input"}</p>
              <p className="mt-0.5 line-clamp-1 text-xs text-neutral-400">{run.output || "—"}</p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                  {formatDuration(run.duration_ms)}
                </span>
                <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                  {run.step_count || 0} steps
                </span>
                <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-500">
                  {fmtTime(run.create_time)}
                </span>
              </div>
            </div>
            <div className="shrink-0 text-right">
              <RunStatusBadge run={run} />
            </div>
          </div>
        </div>
      </button>
    </motion.li>
  );
}

export default function RunsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [runs, setRuns] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [filterWf, setFilterWf] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rows, wfs] = await Promise.all([
        listWorkspaceRuns({ limit: 50, workflow_id: filterWf || undefined }).catch(() => []),
        getWorkflowsPage({ pageSize: 50 }).catch(() => ({ data: [] })),
      ]);
      setRuns(Array.isArray(rows) ? rows : []);
      setWorkflows(wfs?.data || []);
      setError("");
    } catch (err) {
      setError(err.message || "Failed to load runs");
    } finally {
      setLoading(false);
    }
  }, [filterWf]);

  useEffect(() => {
    getUserInfo()
      .then((u) => {
        if (!u) {
          router.replace("/login");
          return;
        }
        setUser(u);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const filteredRuns = useMemo(() => {
    const q = search.trim().toLowerCase();
    return runs.filter((run) => {
      if (filterStatus === "success" && isRunError(run)) return false;
      if (filterStatus === "error" && !isRunError(run)) return false;
      if (!q) return true;
      const hay = [run.workflow_name, run.input, run.output, String(run.id)].filter(Boolean).join(" ").toLowerCase();
      return hay.includes(q);
    });
  }, [runs, filterStatus, search]);

  const stats = useMemo(() => {
    const total = runs.length;
    const errors = runs.filter(isRunError).length;
    const success = total - errors;
    const avgMs = total ? Math.round(runs.reduce((s, r) => s + (r.duration_ms || 0), 0) / total) : 0;
    const rate = total ? Math.round((success / total) * 100) : 0;
    return { total, errors, success, avgMs, rate };
  }, [runs]);

  async function openDetail(id) {
    if (detail?.id === id) return;
    setDetailBusy(true);
    setError("");
    try {
      setDetail(await getWorkflowRun(id));
    } catch (err) {
      setError(err.message || "Failed to load run");
      setDetail(null);
    } finally {
      setDetailBusy(false);
    }
  }

  return (
    <WorkspacePageShell user={user} loading={loading || !user} loadingMessage="Loading runs…" maxWidth="max-w-7xl">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
        <WorkspaceHero
          eyebrow="Operations"
          title="Run"
          titleHighlight="history"
          description="Every workflow execution across the workspace — filter pipelines, inspect step timelines, and export receipts."
          badge={
            <span className="workspace-badge-live inline-flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-neutral-400 opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-neutral-900" />
              </span>
              {filteredRuns.length} runs
            </span>
          }
        />

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5, ease }}
          className="mt-8 grid gap-4 sm:grid-cols-3"
        >
          <WorkspaceStatCard
            label="Total runs"
            value={<AnimatedCounter value={String(stats.total)} />}
            hint="Loaded in view"
          />
          <WorkspaceStatCard
            label="Success rate"
            value={<AnimatedCounter value={`${stats.rate}%`} />}
            hint={`${stats.success} ok · ${stats.errors} failed`}
          />
          <WorkspaceStatCard
            label="Avg duration"
            value={<AnimatedCounter value={formatDuration(stats.avgMs)} />}
            hint="Across loaded runs"
          />
        </motion.div>

        <AnimatePresence mode="wait">
          {error && (
            <motion.div
              key="err"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-6 overflow-hidden"
            >
              <WorkspaceAlert type="error">{error}</WorkspaceAlert>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, ease }}
          className="workspace-panel noise mt-10 rounded-[1.5rem] p-5 sm:p-6"
        >
          <p className="workspace-section-label">Filters</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <label className="block sm:col-span-2">
              <span className="text-xs font-semibold text-neutral-700">Search</span>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Workflow, input, output, run id…"
                className="input-field mt-2 w-full text-sm"
              />
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-neutral-700">Workflow</span>
              <select value={filterWf} onChange={(e) => setFilterWf(e.target.value)} className="input-field mt-2 w-full text-sm">
                <option value="">All workflows</option>
                {workflows.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-neutral-700">Status</span>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="input-field mt-2 w-full text-sm"
              >
                <option value="all">All statuses</option>
                <option value="success">Completed</option>
                <option value="error">Failed</option>
              </select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={load} className="btn-secondary text-sm">
              Refresh
            </button>
            <Link href="/workflows" className="workspace-btn-ghost text-sm">
              Open workflows →
            </Link>
          </div>
        </motion.div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(300px,380px)]">
          <section>
            <div className="mb-4 flex items-end justify-between gap-3">
              <div>
                <p className="workspace-section-label">Timeline</p>
                <h2 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">Recent executions</h2>
              </div>
              <span className="text-xs text-neutral-500">{filteredRuns.length} shown</span>
            </div>

            {filteredRuns.length === 0 ? (
              <WorkspaceEmpty
                title="No runs found"
                description={
                  runs.length === 0
                    ? "Publish and execute a workflow to populate history."
                    : "Try adjusting your filters or search query."
                }
                actionLabel="Go to workflows"
                actionHref="/workflows"
                icon="▸"
              />
            ) : (
              <ul className="space-y-2.5">
                {filteredRuns.map((run, i) => (
                  <RunCard
                    key={run.id}
                    run={run}
                    index={i}
                    active={detail?.id === run.id}
                    onSelect={openDetail}
                  />
                ))}
              </ul>
            )}
          </section>

          <aside className="lg:sticky lg:top-24 lg:self-start">
            <motion.div layout className="workspace-panel noise overflow-hidden rounded-[1.5rem]">
              <div className="border-b border-black/[0.06] bg-gradient-to-r from-neutral-50 to-white px-5 py-4 sm:px-6">
                <p className="text-[11px] font-semibold tracking-[0.16em] text-neutral-400 uppercase">Run inspector</p>
                <h3 className="mt-1 font-serif text-lg tracking-tight text-neutral-900">
                  {detail ? `Run #${detail.id}` : "Select a run"}
                </h3>
              </div>

              <div className="p-5 sm:p-6">
                {detailBusy && (
                  <div className="space-y-3">
                    {[0, 1, 2].map((i) => (
                      <motion.div
                        key={i}
                        className="h-12 rounded-xl bg-neutral-100"
                        animate={{ opacity: [0.4, 0.8, 0.4] }}
                        transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.15 }}
                      />
                    ))}
                  </div>
                )}

                {!detailBusy && !detail && (
                  <div className="py-8 text-center">
                    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border-2 border-dashed border-neutral-300">
                      <svg className="h-6 w-6 text-neutral-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M4 6h16M4 12h10M4 18h6" />
                      </svg>
                    </div>
                    <p className="mt-4 text-sm text-neutral-500">Click a run on the left to inspect its step timeline.</p>
                  </div>
                )}

                <AnimatePresence mode="wait">
                  {detail && !detailBusy && (
                    <motion.div
                      key={detail.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.35, ease }}
                      className="space-y-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <RunStatusBadge run={detail} large />
                        <span className="text-xs text-neutral-500">{fmtTime(detail.create_time)}</span>
                      </div>

                      <p className="text-sm font-semibold text-neutral-900">{detail.workflow_name || detail.workflow_id}</p>

                      <div className="flex flex-wrap gap-2">
                        <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[10px] font-medium text-neutral-600">
                          {formatDuration(detail.duration_ms)}
                        </span>
                        <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[10px] font-medium text-neutral-600">
                          {(detail.steps || []).length || detail.step_count || 0} steps
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <button type="button" className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]" onClick={() => exportRunJson(detail)}>
                          JSON
                        </button>
                        <button type="button" className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]" onClick={() => exportRunMd(detail)}>
                          Markdown
                        </button>
                        <button type="button" className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]" onClick={() => exportRunCsv(detail)}>
                          CSV
                        </button>
                      </div>

                      {(detail.input || detail.output) && (
                        <div className="space-y-3 rounded-xl border border-black/[0.06] bg-neutral-50/60 p-3">
                          {detail.input && (
                            <div>
                              <p className="text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">Input</p>
                              <p className="mt-1 line-clamp-3 whitespace-pre-wrap text-[11px] leading-relaxed text-neutral-700">{detail.input}</p>
                            </div>
                          )}
                          {detail.output && (
                            <div>
                              <p className="text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">Output</p>
                              <p className="mt-1 line-clamp-4 whitespace-pre-wrap text-[11px] leading-relaxed text-neutral-700">{detail.output}</p>
                            </div>
                          )}
                        </div>
                      )}

                      <div>
                        <p className="mb-3 text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">Step timeline</p>
                        <div className="max-h-[22rem] overflow-y-auto pr-1">
                          <StepTimeline steps={detail.steps} />
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          </aside>
        </div>
      </motion.div>
    </WorkspacePageShell>
  );
}
