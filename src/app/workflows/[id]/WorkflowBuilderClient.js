"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import Logo from "@/components/Logo";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkflowCanvas, { NODE_META, nodeSubtitle } from "@/components/workflow/WorkflowCanvas";
import WorkflowInspector from "@/components/workflow/WorkflowInspector";
import { NODE_ICONS } from "@/components/workflow/WorkflowNodeIcons";
import { getUserInfo } from "@/lib/api/auth";
import { listKnowledge } from "@/lib/api/knowledge";
import {
  deleteWorkflow,
  getWorkflowInfo,
  getWorkflowSchedules,
  getWorkflowVersions,
  createWorkflowSchedule,
  updateWorkflowSchedule,
  deleteWorkflowSchedule,
  restoreWorkflowVersion,
  resumeWorkflow,
  runWorkflowWs,
  setWorkflowStatus,
  updateWorkflow,
} from "@/lib/api/workflows";
import { setWorkflowPublic } from "@/lib/api/marketplace";

const ease = [0.16, 1, 0.3, 1];

const ADD_NODE_DEFAULTS = {
  transform: { template: "{{input}}" },
  condition: { keyword: "", then_text: "{{input}}", else_text: "" },
  http: { url: "", method: "GET", body: "" },
  retrieve: { knowledge_id: null, limit: 5 },
  llm: { prompt: "You are a helpful assistant." },
  output: { label: "Output" },
  loop: { max: 5, prompt: "Process: {{item}}", separator: "\n" },
  parallel: { branches: ["Summary", "Key points", "Actions"] },
  human: { message: "Review:\n{{output}}", require_approval: false },
  agent: { tools: ["summarize"], prompt: "You are a capable agent.", knowledge_id: null },
  subgraph: { workflow_id: null, label: "Sub-workflow" },
};

export default function WorkflowBuilderClient({ workflowId }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [inspectorTab, setInspectorTab] = useState("configure");

  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [status, setStatus] = useState(0);
  const [webhookToken, setWebhookToken] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [versions, setVersions] = useState([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [schedules, setSchedules] = useState([]);
  const [scheduleCron, setScheduleCron] = useState("0 9 * * *");
  const [scheduleInput, setScheduleInput] = useState("Scheduled run");
  const [scheduleBusy, setScheduleBusy] = useState(false);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [selectedId, setSelectedId] = useState(null);
  const [libraries, setLibraries] = useState([]);
  const [runInput, setRunInput] = useState("");
  const [runResult, setRunResult] = useState(null);
  const [pendingReview, setPendingReview] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);

  const selected = useMemo(
    () => graph.nodes?.find((n) => n.id === selectedId) || null,
    [graph.nodes, selectedId]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [info, kbRes] = await Promise.all([
        getWorkflowInfo(workflowId),
        listKnowledge({ pageSize: 100 }),
      ]);
      setName(info?.name || "");
      setDesc(info?.desc || "");
      setStatus(info?.status ?? 0);
      setWebhookToken(info?.webhook_token || "");
      setIsPublic(!!info?.is_public);
      setGraph(info?.graph || { nodes: [], edges: [] });
      setRecentRuns(info?.recent_runs || []);
      setLibraries(kbRes?.data || []);
      if (info?.graph?.nodes?.[0]) setSelectedId(info.graph.nodes[0].id);
    } catch (err) {
      setError(err.message || "Workflow not found");
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const loadVersions = useCallback(async () => {
    setVersionsLoading(true);
    try {
      const rows = await getWorkflowVersions(workflowId);
      setVersions(Array.isArray(rows) ? rows : rows?.data || []);
    } catch {
      setVersions([]);
    } finally {
      setVersionsLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    if (inspectorTab === "history" && user) loadVersions();
  }, [inspectorTab, user, loadVersions]);

  const loadSchedules = useCallback(async () => {
    try {
      const rows = await getWorkflowSchedules(workflowId);
      setSchedules(Array.isArray(rows) ? rows : rows?.data || []);
    } catch {
      setSchedules([]);
    }
  }, [workflowId]);

  useEffect(() => {
    if (user && status === 1) loadSchedules();
  }, [user, status, loadSchedules]);

  function updateNode(id, patch) {
    setGraph((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) =>
        n.id === id ? { ...n, ...patch, data: { ...n.data, ...(patch.data || {}) } } : n
      ),
    }));
    setSaved(false);
  }

  function addNode(type) {
    if (user?.role === "viewer") return;
    const id = `${type}_${Date.now()}`;
    const maxX = Math.max(60, ...(graph.nodes || []).map((n) => n.x || 0));
    const newNode = {
      id,
      type,
      x: maxX + 200,
      y: 120 + ((graph.nodes?.length || 0) % 4) * 80,
      data: { ...(ADD_NODE_DEFAULTS[type] || {}) },
    };
    setGraph((prev) => ({
      ...prev,
      nodes: [...(prev.nodes || []), newNode],
    }));
    setSelectedId(id);
    setInspectorTab("configure");
    setSaved(false);
  }

  function connectNodes(fromId, toId) {
    if (!fromId || !toId || fromId === toId) return;
    setGraph((prev) => {
      const exists = (prev.edges || []).some((e) => e.from === fromId && e.to === toId);
      if (exists) return prev;
      return { ...prev, edges: [...(prev.edges || []), { from: fromId, to: toId }] };
    });
    setSaved(false);
  }

  function disconnectEdge(fromId, toId) {
    setGraph((prev) => ({
      ...prev,
      edges: (prev.edges || []).filter((e) => !(e.from === fromId && e.to === toId)),
    }));
    setSaved(false);
  }

  function deleteNode(nodeId) {
    if (user?.role === "viewer") return;
    const remaining = (graph.nodes || []).filter((n) => n.id !== nodeId);
    setGraph((prev) => ({
      ...prev,
      nodes: (prev.nodes || []).filter((n) => n.id !== nodeId),
      edges: (prev.edges || []).filter((e) => e.from !== nodeId && e.to !== nodeId),
    }));
    setSelectedId((id) => (id === nodeId ? remaining[0]?.id ?? null : id));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await updateWorkflow({ id: workflowId, name: name.trim(), desc, graph });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleResume(approved) {
    if (!pendingReview?.id) return;
    setRunning(true);
    setError("");
    try {
      const res = await resumeWorkflow(pendingReview.id, { approved });
      setPendingReview(null);
      setRunResult({ output: res.output, steps: res.steps, duration_ms: res.duration_ms });
    } catch (err) {
      setError(err.message || "Resume failed");
    } finally {
      setRunning(false);
    }
  }

  async function handleTogglePublic() {
    if (status !== 1) {
      setError("Publish the workflow before sharing to marketplace.");
      return;
    }
    try {
      const next = !isPublic;
      await setWorkflowPublic(workflowId, next);
      setIsPublic(next);
    } catch (err) {
      setError(err.message || "Share update failed");
    }
  }

  async function handleRestoreVersion(versionId) {
    if (!confirm("Restore this version? Current draft will be snapshotted first.")) return;
    setSaving(true);
    setError("");
    try {
      const info = await restoreWorkflowVersion(workflowId, versionId);
      setName(info?.name || "");
      setDesc(info?.desc || "");
      setGraph(info?.graph || { nodes: [], edges: [] });
      await loadVersions();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err.message || "Restore failed");
    } finally {
      setSaving(false);
    }
  }

  function webhookUrl() {
    if (!webhookToken || typeof window === "undefined") return "";
    return `${window.location.origin}/api/v1/workflow/webhook/${webhookToken}`;
  }

  async function handleCreateSchedule() {
    setScheduleBusy(true);
    setError("");
    try {
      await createWorkflowSchedule(workflowId, {
        cron_expression: scheduleCron.trim(),
        input_text: scheduleInput.trim(),
      });
      await loadSchedules();
    } catch (err) {
      setError(err.message || "Schedule failed");
    } finally {
      setScheduleBusy(false);
    }
  }

  async function handleToggleSchedule(sched) {
    setScheduleBusy(true);
    try {
      await updateWorkflowSchedule(sched.id, { enabled: !sched.enabled });
      await loadSchedules();
    } catch (err) {
      setError(err.message || "Schedule update failed");
    } finally {
      setScheduleBusy(false);
    }
  }

  async function handleDeleteSchedule(id) {
    setScheduleBusy(true);
    try {
      await deleteWorkflowSchedule(id);
      await loadSchedules();
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setScheduleBusy(false);
    }
  }

  async function handleRun() {
    if (!runInput.trim() || readOnly) return;
    setRunning(true);
    setRunResult({ output: "", steps: [] });
    setError("");
    setInspectorTab("test");
    const steps = [];
    let streamOutput = "";
    try {
      await updateWorkflow({ id: workflowId, name: name.trim(), desc, graph });
      await runWorkflowWs(workflowId, runInput.trim(), {
        onHumanReview: (data) => {
          setPendingReview({ id: data.pending_run_id, message: data.message });
        },
        onStep: (data) => {
          if (data.phase === "done" && data.step) {
            const idx = steps.findIndex((s) => s.node_id === data.step.node_id);
            if (idx >= 0) steps[idx] = data.step;
            else steps.push(data.step);
            setRunResult({
              output: streamOutput,
              steps: [...steps],
            });
          } else if (data.phase === "start" && data.step) {
            setRunResult((prev) => ({
              output: prev?.output || streamOutput,
              steps: [...steps, { ...data.step, status: "running" }],
            }));
          }
        },
        onStream: (token) => {
          streamOutput += token;
          setRunResult((prev) => ({
            output: streamOutput,
            steps: prev?.steps || [...steps],
          }));
        },
        onComplete: (data) => {
          if (data.status === "pending_human") {
            setPendingReview({ id: data.pending_run_id, message: "Approval required" });
          }
          setRunResult({
            output: data.output,
            steps: data.steps,
            duration_ms: data.duration_ms,
          });
        },
      });
      await load();
    } catch (err) {
      setError(err.message || "Run failed");
    } finally {
      setRunning(false);
    }
  }

  async function togglePublish() {
    try {
      const res = await setWorkflowStatus(workflowId, status === 1 ? 0 : 1);
      const next = status === 1 ? 0 : 1;
      setStatus(next);
      if (res?.webhook_token) setWebhookToken(res.webhook_token);
      if (next === 0) setIsPublic(false);
    } catch (err) {
      setError(err.message || "Status update failed");
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this workflow permanently?")) return;
    try {
      await deleteWorkflow(workflowId);
      router.push("/workflows");
    } catch (err) {
      setError(err.message || "Delete failed");
    }
  }

  if (!user) {
    return (
      <div className="relative flex h-screen items-center justify-center">
        <WorkspaceLiveBackground />
        <span className="relative z-10 text-neutral-500">Loading studio…</span>
      </div>
    );
  }

  const readOnly = user.role === "viewer";

  return (
    <div className="workflow-studio relative flex h-screen flex-col overflow-hidden">
      <WorkspaceLiveBackground active={saving || running} />

      <motion.header
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ease }}
        className="workflow-studio-toolbar relative z-20 shrink-0 border-b border-white/60 px-3 py-2 sm:px-4 sm:py-2.5"
      >
        <div className="flex items-center gap-2 sm:gap-2.5">
          <Link href="/workflows" className="workspace-btn-ghost shrink-0 !px-2.5 !py-1.5 text-xs">
            ← Back
          </Link>
          <div className="hidden sm:block shrink-0">
            <Logo size="sm" />
          </div>
        </div>

        <div className="min-w-0 border-l border-black/[0.06] pl-2.5 sm:pl-3">
          <div className="flex items-center gap-2">
            <input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setSaved(false);
              }}
              disabled={loading || readOnly}
              className="min-w-0 flex-1 truncate bg-transparent font-serif text-sm tracking-tight outline-none sm:text-lg"
              placeholder="Workflow name"
            />
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                status === 1 ? "bg-emerald-500/15 text-emerald-700" : "bg-neutral-100 text-neutral-500"
              }`}
            >
              {status === 1 ? "Live" : "Draft"}
            </span>
          </div>
          <input
            value={desc}
            onChange={(e) => {
              setDesc(e.target.value);
              setSaved(false);
            }}
            disabled={loading || readOnly}
            className="mt-0.5 hidden w-full truncate bg-transparent text-[11px] text-neutral-500 outline-none md:block"
            placeholder="Add a short description…"
          />
        </div>

        <div className="flex shrink-0 items-center justify-end gap-1">
          {saved && (
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="hidden text-[11px] font-semibold text-emerald-600 lg:inline"
            >
              Saved
            </motion.span>
          )}
          {!readOnly && (
            <>
              <button
                type="button"
                onClick={() => setInspectorTab("test")}
                className="workspace-btn-ghost hidden !px-2.5 !py-1.5 text-xs lg:inline-flex"
              >
                Test
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || loading}
                className="btn-primary !px-3 !py-1.5 text-xs"
              >
                {saving ? "…" : "Save"}
              </button>
              <button
                type="button"
                onClick={togglePublish}
                className="workspace-btn-ghost hidden !px-2.5 !py-1.5 text-xs xl:inline-flex"
              >
                {status === 1 ? "Unpub" : "Publish"}
              </button>
              {status === 1 && (
                <button
                  type="button"
                  onClick={handleTogglePublic}
                  className={`workspace-btn-ghost hidden !px-2.5 !py-1.5 text-xs xl:inline-flex ${
                    isPublic ? "!bg-violet-100 !text-violet-800" : ""
                  }`}
                >
                  {isPublic ? "Listed" : "Share"}
                </button>
              )}
              <button
                type="button"
                onClick={handleDelete}
                className="workspace-btn-ghost workspace-btn-danger !px-2.5 !py-1.5 text-xs"
              >
                Delete
              </button>
            </>
          )}
        </div>
      </motion.header>

      {error && (
        <div className="relative z-20 shrink-0 border-b border-red-100 bg-red-50/90 px-4 py-2 text-center text-sm text-red-700">
          {error}
        </div>
      )}

      {readOnly && (
        <div className="relative z-20 shrink-0 border-b border-amber-100 bg-amber-50/90 px-4 py-2 text-center text-sm text-amber-800">
          Viewer access — you can inspect workflows but cannot edit or run them.
        </div>
      )}

      <div className="relative z-10 flex min-h-0 flex-1">
        <aside className="workflow-studio-rail hidden w-[240px] shrink-0 flex-col border-r border-white/60 lg:flex">
          <div className="border-b border-black/[0.04] p-4">
            <p className="workspace-section-label">Pipeline</p>
              <p className="mt-1 text-xs text-neutral-500">
              {graph.nodes?.length || 0} nodes · connect in Configure panel
            </p>
          </div>
          <ul className="min-h-0 flex-1 space-y-0 overflow-y-auto p-3">
            {(graph.nodes || []).map((node, i) => {
              const Icon = NODE_ICONS[node.type] || NODE_ICONS.output;
              const meta = NODE_META[node.type];
              const active = selectedId === node.id;
              const isLast = i === (graph.nodes?.length || 0) - 1;
              return (
                <li key={node.id}>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedId(node.id);
                        setInspectorTab("configure");
                      }}
                      className={`flex min-w-0 flex-1 items-center gap-3 rounded-2xl px-3 py-2.5 text-left transition-all ${
                        active
                          ? "bg-neutral-900 text-white shadow-lg shadow-neutral-900/15"
                          : "bg-white/50 hover:bg-white/85"
                      }`}
                    >
                      <span
                        className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 ${
                          active
                            ? "border-white/30 bg-white/10 wf-rail-active-ring"
                            : `border-transparent ${meta?.accent || ""} bg-white/90`
                        }`}
                      >
                        <Icon size={16} />
                        {active && (
                          <span
                            className="absolute -inset-1 rounded-full border border-dashed border-white/40 animate-spin"
                            style={{ animationDuration: "8s" }}
                          />
                        )}
                        {running && (
                          <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-white animate-pulse" />
                        )}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-[9px] font-bold uppercase tracking-[0.14em] opacity-60">
                          Step {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="block truncate text-xs font-semibold">{nodeSubtitle(node)}</span>
                      </span>
                    </button>
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={() => deleteNode(node.id)}
                        className={`shrink-0 rounded-xl px-2 py-2 text-xs font-semibold transition-colors ${
                          active
                            ? "text-white/70 hover:bg-white/10 hover:text-white"
                            : "text-neutral-400 hover:bg-red-50 hover:text-red-600"
                        }`}
                        title="Delete node"
                        aria-label={`Delete ${nodeSubtitle(node)}`}
                      >
                        ×
                      </button>
                    )}
                  </div>
                  {!isLast && <div className="wf-rail-connector" aria-hidden />}
                </li>
              );
            })}
          </ul>
          {!readOnly && (
            <div className="shrink-0 border-t border-black/[0.04] p-3">
              <p className="workspace-section-label mb-2">Add node</p>
              <div className="flex flex-wrap gap-1.5">
                {["loop", "parallel", "agent", "human", "subgraph", "transform", "condition", "http", "retrieve", "llm", "output"].map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => addNode(type)}
                    className="rounded-lg bg-white/70 px-2.5 py-1.5 text-[10px] font-semibold capitalize text-neutral-600 ring-1 ring-black/[0.06] hover:bg-white"
                  >
                    + {type}
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        <main className="workflow-studio-main min-w-0 flex-1 p-2 sm:p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.985 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.04, ease }}
            className="workspace-panel h-full overflow-hidden rounded-[1.25rem] sm:rounded-[1.75rem]"
          >
            {loading ? (
              <div className="flex h-full flex-col items-center justify-center gap-3">
                <div className="h-12 w-12 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900" />
                <p className="text-sm text-neutral-500">Loading canvas…</p>
              </div>
            ) : (
              <WorkflowCanvas
                key={workflowId}
                graph={graph}
                onChange={
                  readOnly
                    ? undefined
                    : (g) => {
                        setGraph(g);
                        setSaved(false);
                      }
                }
                selectedId={selectedId}
                onSelect={setSelectedId}
                flowing={running}
                readOnly={readOnly}
              />
            )}
          </motion.div>
        </main>

        <WorkflowInspector
          tab={inspectorTab}
          onTabChange={setInspectorTab}
          selected={selected}
          nodes={graph.nodes || []}
          edges={graph.edges || []}
          knowledgeBases={libraries}
          onUpdateNode={readOnly ? () => {} : updateNode}
          onConnect={readOnly ? undefined : connectNodes}
          onDisconnect={readOnly ? undefined : disconnectEdge}
          onDeleteNode={readOnly ? undefined : deleteNode}
          runInput={runInput}
          onRunInputChange={setRunInput}
          onRun={handleRun}
          running={running}
          runResult={runResult}
          pendingReview={pendingReview}
          onResume={handleResume}
          recentRuns={recentRuns}
          versions={versions}
          versionsLoading={versionsLoading}
          onRestoreVersion={readOnly ? undefined : handleRestoreVersion}
          workflowStatus={status}
          webhookUrl={webhookUrl()}
          isPublic={isPublic}
          onTogglePublic={readOnly ? undefined : handleTogglePublic}
          schedules={schedules}
          scheduleCron={scheduleCron}
          scheduleInput={scheduleInput}
          onScheduleCronChange={setScheduleCron}
          onScheduleInputChange={setScheduleInput}
          onCreateSchedule={readOnly || status !== 1 ? undefined : handleCreateSchedule}
          onToggleSchedule={readOnly ? undefined : handleToggleSchedule}
          onDeleteSchedule={readOnly ? undefined : handleDeleteSchedule}
          scheduleBusy={scheduleBusy}
          readOnly={readOnly}
        />
      </div>
    </div>
  );
}
