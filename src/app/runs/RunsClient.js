"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { getWorkflowRun, getWorkflowsPage, listWorkspaceRuns } from "@/lib/api/workflows";

const ease = [0.16, 1, 0.3, 1];

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function RunsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [runs, setRuns] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [filterWf, setFilterWf] = useState("");
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
    } catch (err) {
      setError(err.message || "Failed to load runs");
    } finally {
      setLoading(false);
    }
  }, [filterWf]);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  async function openDetail(id) {
    setDetailBusy(true);
    setError("");
    try {
      setDetail(await getWorkflowRun(id));
    } catch (err) {
      setError(err.message || "Failed to load run");
    } finally {
      setDetailBusy(false);
    }
  }

  if (!user || loading) {
    return (
      <>
        <AppHeader user={user} />
        <WorkspaceLiveBackground />
        <WorkspaceLoading message="Loading runs…" />
      </>
    );
  }

  return (
    <>
      <AppHeader user={user} />
      <WorkspaceLiveBackground />
      <main className="relative z-10 mx-auto max-w-6xl px-4 pb-16 pt-8 sm:px-6">
        <WorkspaceHero
          eyebrow="Ops"
          title="Run history"
          description="Every workflow execution across the workspace — filter by pipeline and inspect step timelines."
        />

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <WorkspaceStatCard label="Runs loaded" value={String(runs.length)} />
          <WorkspaceStatCard label="Workflows" value={String(workflows.length)} />
          <WorkspaceStatCard
            label="Avg duration"
            value={
              runs.length
                ? `${Math.round(runs.reduce((s, r) => s + (r.duration_ms || 0), 0) / runs.length)}ms`
                : "—"
            }
          />
        </div>

        {error && (
          <div className="mt-6">
            <WorkspaceAlert tone="danger">{error}</WorkspaceAlert>
          </div>
        )}

        <div className="mt-8 flex flex-wrap items-end gap-3">
          <label className="block min-w-[220px] flex-1">
            <span className="text-xs font-semibold text-neutral-600">Filter workflow</span>
            <select
              value={filterWf}
              onChange={(e) => setFilterWf(e.target.value)}
              className="input-field mt-2 w-full text-sm"
            >
              <option value="">All workflows</option>
              {workflows.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={load} className="btn-secondary text-sm">
            Refresh
          </button>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
          <ul className="space-y-2">
            {runs.length === 0 ? (
              <li className="rounded-2xl border border-dashed border-black/10 bg-white/50 px-6 py-12 text-center text-sm text-neutral-500">
                No runs yet. Publish and execute a workflow to populate history.
              </li>
            ) : (
              runs.map((run, i) => (
                <motion.li
                  key={run.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02, ease }}
                >
                  <button
                    type="button"
                    onClick={() => openDetail(run.id)}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      detail?.id === run.id
                        ? "border-neutral-900/20 bg-white shadow-md"
                        : "border-black/[0.06] bg-white/80 hover:shadow-sm"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          href={`/workflows/${run.workflow_id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-semibold text-neutral-900 hover:underline"
                        >
                          {run.workflow_name || run.workflow_id}
                        </Link>
                        <p className="mt-1 truncate text-sm text-neutral-600">{run.input || "—"}</p>
                        <p className="mt-1 truncate text-xs text-neutral-400">{run.output}</p>
                      </div>
                      <div className="shrink-0 text-right text-[10px] text-neutral-400">
                        <p
                          className={`inline-flex rounded-full px-2 py-0.5 font-semibold uppercase tracking-wide ${
                            run.status === 2 || run.status_label === "error"
                              ? "bg-red-50 text-red-700"
                              : "bg-emerald-50 text-emerald-700"
                          }`}
                        >
                          {run.status_label || (run.status === 2 ? "error" : "completed")}
                        </p>
                        <p className="mt-1">{run.duration_ms}ms</p>
                        <p>{run.step_count || 0} steps</p>
                        <p className="mt-1">{fmtTime(run.create_time)}</p>
                      </div>
                    </div>
                  </button>
                </motion.li>
              ))
            )}
          </ul>

          <aside className="workspace-panel h-fit rounded-2xl p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">Step detail</p>
            {detailBusy && <p className="mt-4 text-sm text-neutral-500">Loading…</p>}
            {!detailBusy && !detail && (
              <p className="mt-4 text-sm text-neutral-500">Select a run to inspect its steps.</p>
            )}
            {detail && !detailBusy && (
              <div className="mt-3 space-y-3">
                <p className="text-sm font-semibold text-neutral-900">
                  #{detail.id} · {detail.workflow_name}
                </p>
                <p className="text-xs text-neutral-500">{detail.duration_ms}ms · {fmtTime(detail.create_time)}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]"
                    onClick={() => {
                      const blob = new Blob([JSON.stringify(detail, null, 2)], { type: "application/json" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `run-${detail.id}.json`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Export JSON
                  </button>
                  <button
                    type="button"
                    className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]"
                    onClick={() => {
                      const lines = [
                        `# Run #${detail.id} — ${detail.workflow_name || ""}`,
                        "",
                        `- Status: ${detail.status_label || detail.status || "—"}`,
                        `- Duration: ${detail.duration_ms || 0}ms`,
                        `- Created: ${detail.create_time || "—"}`,
                        "",
                        "## Input",
                        "",
                        detail.input || "—",
                        "",
                        "## Output",
                        "",
                        detail.output || "—",
                        "",
                        "## Steps",
                        "",
                      ];
                      (detail.steps || []).forEach((step, i) => {
                        lines.push(`### ${i + 1}. ${step.type || step.node_type || "step"} (${step.status || "—"})`);
                        lines.push("");
                        lines.push(step.output || step.message || "—");
                        lines.push("");
                      });
                      const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `run-${detail.id}.md`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Export MD
                  </button>
                </div>
                <div className="max-h-[28rem] space-y-2 overflow-y-auto">
                  {(detail.steps || []).map((step, i) => (
                    <div key={i} className="rounded-xl border border-black/[0.05] bg-neutral-50 px-3 py-2">
                      <p className="text-[11px] font-semibold">
                        {step.type || step.node_type || "step"}
                        <span
                          className={`ml-2 font-normal ${
                            step.status === "ok"
                              ? "text-emerald-600"
                              : step.status === "error"
                                ? "text-red-600"
                                : "text-neutral-400"
                          }`}
                        >
                          {step.status || "—"}
                        </span>
                      </p>
                      <p className="mt-1 line-clamp-4 text-[10px] text-neutral-500">
                        {step.output || step.message || "—"}
                      </p>
                    </div>
                  ))}
                  {!(detail.steps || []).length && (
                    <p className="text-xs text-neutral-400">No step payload for this run.</p>
                  )}
                </div>
              </div>
            )}
          </aside>
        </div>
      </main>
    </>
  );
}
