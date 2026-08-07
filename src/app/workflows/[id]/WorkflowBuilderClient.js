"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import Logo from "@/components/Logo";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkflowCanvas, { NODE_META, nodeSubtitle } from "@/components/workflow/WorkflowCanvas";
import WorkflowDiffSplit from "@/components/workflow/WorkflowDiffSplit";
import WorkflowInspector from "@/components/workflow/WorkflowInspector";
import { NODE_ICONS } from "@/components/workflow/WorkflowNodeIcons";
import { getUserInfo } from "@/lib/api/auth";
import { ensureActiveWorkspace } from "@/lib/api/workspaces";
import { listKnowledge } from "@/lib/api/knowledge";
import {
  deleteWorkflow,
  getWorkflowInfo,
  getWorkflowSchedules,
  getWorkflowVersions,
  getWorkflowVersionDiff,
  getWorkflowPresence,
  touchWorkflowPresence,
  createWorkflowSchedule,
  updateWorkflowSchedule,
  deleteWorkflowSchedule,
  restoreWorkflowVersion,
  resumeWorkflow,
  runWorkflowWs,
  setWorkflowStatus,
  updateWorkflow,
  getWorkflowsPage,
  validateWorkflowGraph,
} from "@/lib/api/workflows";
import {
  downloadWorkflowDiffJson,
  downloadWorkflowDiffMarkdown,
} from "@/lib/workflow/diffExport";
import CreateApiNodeModal from "@/components/workflow/CreateApiNodeModal";
import OpenApiImportModal from "@/components/workflow/OpenApiImportModal";
import { useWorkspaceAccess } from "@/lib/auth/workspaceAccess";
import { listNodeLibrary } from "@/lib/api/nodes";

const ease = [0.16, 1, 0.3, 1];
const ease = [0.16, 1, 0.3, 1];

function mergeNodeDataWithSchema(type, data, builtinSchemas) {
  const schema = builtinSchemas.find((s) => s.type === type);
  const defaults = schema?.defaults || ADD_NODE_DEFAULTS[type] || {};
  return { ...defaults, ...(data || {}) };
}

function mergeGraphNodesWithSchemas(nodes, builtinSchemas) {
  return (nodes || []).map((n) => ({
    ...n,
    data: mergeNodeDataWithSchema(n.type, n.data, builtinSchemas),
  }));
}

const CURSOR_COLORS = ["#8b5cf6", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444"];

const ADD_NODE_DEFAULTS = {
  transform: { template: "{{input}}" },
  condition: { keyword: "", then_text: "{{input}}", else_text: "" },
  http: { label: "HTTP request", url: "", method: "GET", body: "", headers: "", auth: "custom", credential_id: "", set_output: true },
  notify: {
    channel: "telegram",
    to: "{{chat_id}}",
    subject: "NovaFlow",
    message: "{{output}}",
    credential_id: "",
    from: "",
  },
  jira: {
    action: "create",
    project_key: "NF",
    issue_type: "Task",
    issue_key: "",
    summary: "{{output}}",
    description: "{{input}}",
    set_output: true,
  },
  github: {
    action: "create",
    repo: "",
    issue_number: "",
    title: "{{output}}",
    body: "{{input}}",
    labels: "bug",
    set_output: true,
  },
  linear: {
    action: "create",
    team_id: "",
    issue_id: "",
    title: "{{output}}",
    description: "{{input}}",
    set_output: true,
  },
  retrieve: { knowledge_id: null, query: "{{input}}", limit: 6 },
  llm: {
    label: "LLM",
    user_prompt: "{{input}}",
    prompt:
      "Answer clearly. Prefer structure: direct answer, then short supporting bullets. If context is missing, say what is unknown.",
    temperature: 0.7,
  },
  output: { label: "Output", format: "text" },
  loop: {
    max: 5,
    prompt: "For this item, return one compact line: RESULT: <outcome> | WHY: <short reason>\nItem: {{item}}",
    separator: "\n",
  },
  parallel: { branches: ["Summary", "Key points", "Actions"] },
  human: { message: "Review and approve before finalize:\n\n{{output}}", require_approval: true },
  agent: {
    tools: ["summarize"],
    prompt:
      "You are a capable NovaFlow agent. Use tool results as evidence. Answer with: Summary · Details · Confidence (high/med/low).",
    knowledge_id: null,
  },
  subgraph: { workflow_id: null, label: "Sub-workflow" },
  api_node: { node_def_id: "", label: "", set_output: true },
};

export default function WorkflowBuilderClient({ workflowId }) {
  const router = useRouter();
  const safeWorkflowId = useMemo(() => String(workflowId || "").trim(), [workflowId]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [runningNodeId, setRunningNodeId] = useState(null);
  const [mobileRailOpen, setMobileRailOpen] = useState(false);
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
  const [runWebhookUrl, setRunWebhookUrl] = useState("");
  const [versionDiff, setVersionDiff] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffOverlayActive, setDiffOverlayActive] = useState(false);
  const [diffSplitActive, setDiffSplitActive] = useState(false);
  const [presence, setPresence] = useState(null);
  const [presenceViewers, setPresenceViewers] = useState([]);
  const cursorThrottleRef = useRef(0);
  const nodeSeqRef = useRef(0);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [selectedId, setSelectedId] = useState(null);
  const [libraries, setLibraries] = useState([]);
  const [runInput, setRunInput] = useState("");
  const [runResult, setRunResult] = useState(null);
  const [pendingReview, setPendingReview] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);
  const [customNodeDefs, setCustomNodeDefs] = useState([]);
  const [builtinSchemas, setBuiltinSchemas] = useState([]);
  const [dynamicComponents, setDynamicComponents] = useState([]);
  const [workflowList, setWorkflowList] = useState([]);
  const [apiNodeModalOpen, setApiNodeModalOpen] = useState(false);
  const [openApiModalOpen, setOpenApiModalOpen] = useState(false);
  const { readOnly: workspaceReadOnly } = useWorkspaceAccess();

  const schemasMergedRef = useRef(false);

  useEffect(() => {
    if (!builtinSchemas.length || schemasMergedRef.current) return;
    schemasMergedRef.current = true;
    setGraph((g) => {
      const nodes = mergeGraphNodesWithSchemas(g.nodes, builtinSchemas);
      const changed = nodes.some((n, i) => n.data !== g.nodes?.[i]?.data);
      if (!changed) return g;
      return { ...g, nodes };
    });
  }, [builtinSchemas]);

  useEffect(() => {
    if (!selectedId || workspaceReadOnly || !builtinSchemas.length) return;
    setGraph((g) => {
      const node = g.nodes?.find((n) => n.id === selectedId);
      if (!node) return g;
      const merged = mergeNodeDataWithSchema(node.type, node.data, builtinSchemas);
      const needsMerge = Object.keys(merged).some(
        (k) => node.data?.[k] === undefined && merged[k] !== undefined && merged[k] !== ""
      );
      if (!needsMerge) return g;
      return {
        ...g,
        nodes: g.nodes.map((n) => (n.id === selectedId ? { ...n, data: merged } : n)),
      };
    });
  }, [selectedId, builtinSchemas, workspaceReadOnly]);

  const selected = useMemo(
    () => graph.nodes?.find((n) => n.id === selectedId) || null,
    [graph.nodes, selectedId]
  );

  const hasNotifyNode = useMemo(
    () => (graph.nodes || []).some((n) => n.type === "notify"),
    [graph.nodes]
  );

  const load = useCallback(async () => {
    if (!safeWorkflowId || safeWorkflowId === "undefined" || safeWorkflowId === "null") {
      setError("Invalid workflow link. Return to the workflows list and open a workflow again.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const info = await getWorkflowInfo(safeWorkflowId);
      setName(info?.name || "");
      setDesc(info?.desc || "");
      setStatus(info?.status ?? 0);
      setWebhookToken(info?.webhook_token || "");
      setIsPublic(!!info?.is_public);
      setRunWebhookUrl(info?.run_webhook_url || "");
      setGraph(info?.graph || { nodes: [], edges: [] });
      setRecentRuns(info?.recent_runs || []);
      if (info?.graph?.nodes?.[0]) setSelectedId(info.graph.nodes[0].id);
      if (info?.graph?.nodes?.length && typeof window !== "undefined" && window.innerWidth < 1024) {
        setMobileRailOpen(true);
      }
    } catch (err) {
      const msg = err?.message || "Workflow not found";
      if (msg === "Workflow not found") {
        setError(
          "Workflow not found in the current workspace. Switch to the correct workspace from the header, or go back and open the workflow again."
        );
      } else if (
        msg.includes("Cannot reach") ||
        msg.includes("unavailable") ||
        msg.includes("unreachable")
      ) {
        setError(
          `${msg} Ensure the NovaFlow backend is running on port 3001, then click Retry.`
        );
      } else {
        setError(msg);
      }
    }

    try {
      const kbRes = await listKnowledge({ pageSize: 100 });
      setLibraries(kbRes?.data || (Array.isArray(kbRes) ? kbRes : []));
    } catch {
      setLibraries([]);
    }

    try {
      const lib = await listNodeLibrary({ include_drafts: false });
      setCustomNodeDefs(lib?.custom || []);
      setBuiltinSchemas(lib?.builtin || []);
      setDynamicComponents(lib?.dynamic || []);
    } catch {
      setCustomNodeDefs([]);
      setBuiltinSchemas([]);
      setDynamicComponents([]);
    }

    try {
      const wfPage = await getWorkflowsPage({ limit: 100 });
      setWorkflowList(wfPage?.data || wfPage?.items || []);
    } catch {
      setWorkflowList([]);
    } finally {
      setLoading(false);
    }
  }, [safeWorkflowId]);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        await ensureActiveWorkspace();
        setUser(u);
      })
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

  useEffect(() => {
    if (!user || workspaceReadOnly) return undefined;
    const syncPresence = () => {
      touchWorkflowPresence(workflowId, {
        cursor_x: cursorThrottleRef.currentX || 0,
        cursor_y: cursorThrottleRef.currentY || 0,
        selected_id: selectedId || "",
      }).catch(() => {});
      getWorkflowPresence(workflowId)
        .then((res) => {
          const viewers = (res?.viewers || []).filter((v) => !v.is_self);
          const colored = viewers.map((v, i) => ({
            ...v,
            color: CURSOR_COLORS[i % CURSOR_COLORS.length],
          }));
          setPresenceViewers(colored);
          setPresence(res?.primary && !res.primary.is_self ? res.primary : colored[0] || null);
        })
        .catch(() => {
          setPresenceViewers([]);
          setPresence(null);
        });
    };
    syncPresence();
    const poll = setInterval(syncPresence, 15000);
    return () => clearInterval(poll);
  }, [user, workflowId, selectedId]);

  const handleCursorMove = useCallback(
    (x, y) => {
      cursorThrottleRef.currentX = x;
      cursorThrottleRef.currentY = y;
      const now = Date.now();
      if (now - (cursorThrottleRef.lastSent || 0) < 1200) return;
      cursorThrottleRef.lastSent = now;
      touchWorkflowPresence(workflowId, {
        cursor_x: x,
        cursor_y: y,
        selected_id: selectedId || "",
      }).catch(() => {});
    },
    [workflowId, selectedId]
  );

  function updateNode(id, patch) {
    setGraph((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) =>
        n.id === id ? { ...n, ...patch, data: { ...n.data, ...(patch.data || {}) } } : n
      ),
    }));
    setSaved(false);
  }

  function addApiNode(def) {
    if (workspaceReadOnly || !def?.id) return;
    nodeSeqRef.current += 1;
    const slug = def.slug || "api";
    const id = `api_${slug}_${nodeSeqRef.current}`;
    const maxX = Math.max(60, ...(graph.nodes || []).map((n) => n.x || 0));
    const newNode = {
      id,
      type: "api_node",
      x: maxX + 200,
      y: 120 + ((graph.nodes?.length || 0) % 4) * 80,
      data: {
        node_def_id: def.id,
        label: def.display_name || def.slug,
        set_output: true,
      },
    };
    setGraph((prev) => ({
      ...prev,
      nodes: [...(prev.nodes || []), newNode],
    }));
    setSelectedId(id);
    setInspectorTab("configure");
    setSaved(false);
  }

  function handleApiNodeSaved(def) {
    setCustomNodeDefs((prev) => {
      const exists = prev.some((d) => d.id === def.id);
      if (exists) return prev.map((d) => (d.id === def.id ? def : d));
      return [def, ...prev];
    });
    addApiNode(def);
  }

  function addComponentNode(comp) {
    if (workspaceReadOnly || !comp?.name) return;
    nodeSeqRef.current += 1;
    const id = `component_${comp.name}_${nodeSeqRef.current}`;
    const maxX = Math.max(60, ...(graph.nodes || []).map((n) => n.x || 0));
    const newNode = {
      id,
      type: "component_node",
      x: maxX + 200,
      y: 120 + ((graph.nodes?.length || 0) % 4) * 80,
      data: {
        ...(comp.defaults || {}),
        component_name: comp.name,
        set_output: true,
      },
    };
    setGraph((prev) => ({
      ...prev,
      nodes: [...(prev.nodes || []), newNode],
    }));
    setSelectedId(id);
    setInspectorTab("configure");
    setSaved(false);
  }

  function addNode(type) {
    if (workspaceReadOnly) return;
    nodeSeqRef.current += 1;
    const id = `${type}_${nodeSeqRef.current}_${graph.nodes?.length || 0}`;
    const maxX = Math.max(60, ...(graph.nodes || []).map((n) => n.x || 0));
    const schemaDefaults = builtinSchemas.find((s) => s.type === type)?.defaults;
    const newNode = {
      id,
      type,
      x: maxX + 200,
      y: 120 + ((graph.nodes?.length || 0) % 4) * 80,
      data: { ...(schemaDefaults || ADD_NODE_DEFAULTS[type] || {}) },
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
    if (workspaceReadOnly) return;
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
      await updateWorkflow({
        id: workflowId,
        name: name.trim(),
        desc,
        graph,
        run_webhook_url: runWebhookUrl.trim(),
      });
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

  async function handleCompareVersion(versionId) {
    setDiffLoading(true);
    setVersionDiff(null);
    setDiffOverlayActive(false);
    setDiffSplitActive(false);
    setInspectorTab("history");
    try {
      const diff = await getWorkflowVersionDiff(workflowId, versionId, "current");
      setVersionDiff(diff);
      setDiffOverlayActive(true);
    } catch (err) {
      setError(err.message || "Diff failed");
    } finally {
      setDiffLoading(false);
    }
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
    setRunningNodeId(null);
    setRunResult({ output: "", steps: [] });
    setError("");
    setInspectorTab("test");
    const steps = [];
    let streamOutput = "";
    try {
      const validation = await validateWorkflowGraph({ workflow_id: workflowId, graph });
      const issues = validation?.validation?.issues || [];
      const errors = issues.filter((i) => i.severity === "error");
      if (errors.length) {
        setError(
          `Fix validation errors before run: ${errors
            .slice(0, 3)
            .map((i) => i.message || i.code)
            .join("; ")}`,
        );
        setRunning(false);
        return;
      }
      await updateWorkflow({
        id: workflowId,
        name: name.trim(),
        desc,
        graph,
        run_webhook_url: runWebhookUrl.trim(),
      });
      await runWorkflowWs(workflowId, runInput.trim(), {
        onHumanReview: (data) => {
          setPendingReview({ id: data.pending_run_id, message: data.message });
        },
        onStep: (data) => {
          if (data.phase === "done" && data.step) {
            setRunningNodeId(null);
            const idx = steps.findIndex((s) => s.node_id === data.step.node_id);
            if (idx >= 0) steps[idx] = data.step;
            else steps.push(data.step);
            setRunResult({
              output: streamOutput,
              steps: [...steps],
            });
          } else if (data.phase === "start" && data.step) {
            setRunningNodeId(data.step.node_id);
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
      setRunningNodeId(null);
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

  const readOnly = workspaceReadOnly || user.role === "viewer";

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
          <button
            type="button"
            onClick={() => setMobileRailOpen((v) => !v)}
            className="workspace-btn-ghost !px-2.5 !py-1.5 text-xs lg:hidden"
            aria-label="Toggle pipeline"
          >
            Pipeline
          </button>
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
          <span>{error}</span>
          <button
            type="button"
            onClick={() => load()}
            className="ml-3 rounded-full border border-red-200 bg-white px-3 py-0.5 text-xs font-medium text-red-700 hover:bg-red-50"
          >
            Retry
          </button>
        </div>
      )}

      {readOnly && (
        <div className="relative z-20 shrink-0 border-b border-amber-100 bg-amber-50/90 px-4 py-2 text-center text-sm text-amber-800">
          Viewer access — you can inspect workflows but cannot edit or run them.
        </div>
      )}

      {presence && (
        <div className="relative z-20 shrink-0 border-b border-sky-100 bg-sky-50/90 px-4 py-2 text-center text-sm text-sky-800">
          {presenceViewers.length > 1
            ? `${presenceViewers.map((v) => v.user_name).join(", ")} are also viewing this workflow`
            : `${presence.user_name} is also viewing this workflow`}
        </div>
      )}

      <div className="relative z-10 flex min-h-0 flex-1">
        <aside className={`workflow-studio-rail w-[240px] shrink-0 flex-col border-r border-white/60 ${mobileRailOpen ? "flex" : "hidden"} lg:flex`}>
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
                        {running && runningNodeId === node.id && (
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
                {(builtinSchemas.length > 0
                  ? builtinSchemas.map((s) => s.type)
                  : ["trigger", "loop", "parallel", "agent", "human", "subgraph", "transform", "condition", "http", "notify", "jira", "github", "linear", "retrieve", "llm", "output"]).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => addNode(type)}
                    className="rounded-lg bg-white/70 px-2.5 py-1.5 text-[10px] font-semibold capitalize text-neutral-600 ring-1 ring-black/[0.06] hover:bg-white"
                  >
                    + {builtinSchemas.find((s) => s.type === type)?.label || type}
                  </button>
                ))}
              </div>
              {dynamicComponents.length > 0 && (
                <div className="mt-3">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">AI components</p>
                  <div className="flex flex-wrap gap-1.5">
                    {dynamicComponents.map((comp) => (
                      <button
                        key={comp.name}
                        type="button"
                        onClick={() => addComponentNode(comp)}
                        className="rounded-lg bg-sky-50 px-2.5 py-1.5 text-[10px] font-semibold text-sky-800 ring-1 ring-sky-200 hover:bg-sky-100"
                      >
                        + {comp.label || comp.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {customNodeDefs.length > 0 && (
                <div className="mt-3">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">My API nodes</p>
                  <div className="flex flex-wrap gap-1.5">
                    {customNodeDefs.map((def) => (
                      <button
                        key={def.id}
                        type="button"
                        onClick={() => addApiNode(def)}
                        className="rounded-lg bg-violet-50 px-2.5 py-1.5 text-[10px] font-semibold text-violet-700 ring-1 ring-violet-200 hover:bg-violet-100"
                      >
                        + {def.display_name || def.slug}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <button
                type="button"
                onClick={() => setApiNodeModalOpen(true)}
                className="mt-3 w-full rounded-lg border border-dashed border-violet-300 bg-violet-50/50 px-2 py-2 text-[10px] font-semibold text-violet-700 hover:bg-violet-50"
              >
                + Create API node
              </button>
              <button
                type="button"
                onClick={() => setOpenApiModalOpen(true)}
                className="mt-2 w-full rounded-lg border border-dashed border-sky-300 bg-sky-50/50 px-2 py-2 text-[10px] font-semibold text-sky-700 hover:bg-sky-50"
              >
                Import OpenAPI spec
              </button>
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
            ) : diffSplitActive && versionDiff ? (
              <WorkflowDiffSplit
                fromLabel={versionDiff.from}
                toLabel={versionDiff.to}
                fromGraph={versionDiff.from_graph}
                toGraph={versionDiff.to_graph}
                overlay={versionDiff.overlay}
              />
            ) : (
              <div className="relative h-full">
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
                  diffOverlay={diffOverlayActive && versionDiff?.overlay ? versionDiff.overlay : null}
                  remoteCursors={presenceViewers}
                  onCursorMove={readOnly ? undefined : handleCursorMove}
                />
                {selected && !readOnly ? (
                  <div
                    className="pointer-events-none absolute bottom-3 left-1/2 z-30 flex -translate-x-1/2 gap-2 rounded-full bg-white/95 px-3 py-2 shadow-lg ring-1 ring-black/10"
                    role="toolbar"
                    aria-label="Node actions"
                  >
                    <button
                      type="button"
                      className="pointer-events-auto rounded-full bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white"
                      onClick={handleRun}
                      disabled={running}
                    >
                      Run workflow
                    </button>
                    <button
                      type="button"
                      className="pointer-events-auto rounded-full bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 ring-1 ring-red-200"
                      onClick={() => deleteNode(selected.id)}
                    >
                      Delete node
                    </button>
                  </div>
                ) : null}
              </div>
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
          runWebhookUrl={runWebhookUrl}
          onRunWebhookUrlChange={readOnly ? undefined : setRunWebhookUrl}
          versionDiff={versionDiff}
          diffLoading={diffLoading}
          diffOverlayActive={diffOverlayActive}
          onToggleDiffOverlay={setDiffOverlayActive}
          diffSplitActive={diffSplitActive}
          onToggleDiffSplit={setDiffSplitActive}
          onCompareVersion={readOnly ? undefined : handleCompareVersion}
          onExportDiffJson={
            versionDiff ? () => downloadWorkflowDiffJson(versionDiff, name) : undefined
          }
          onExportDiffMd={
            versionDiff ? () => downloadWorkflowDiffMarkdown(versionDiff, name) : undefined
          }
          readOnly={readOnly}
          workflowId={workflowId}
          hasNotifyNode={hasNotifyNode}
          customNodeDefs={customNodeDefs}
          builtinSchemas={builtinSchemas}
          dynamicComponents={dynamicComponents}
          workflowList={workflowList}
        />
      </div>
      <CreateApiNodeModal
        open={apiNodeModalOpen}
        onClose={() => setApiNodeModalOpen(false)}
        onSaved={handleApiNodeSaved}
      />
      <OpenApiImportModal
        open={openApiModalOpen}
        onClose={() => setOpenApiModalOpen(false)}
        onImported={() => {
          listNodeLibrary().then((lib) => {
            setCustomNodeDefs(lib?.custom || []);
          });
        }}
      />
    </div>
  );
}
