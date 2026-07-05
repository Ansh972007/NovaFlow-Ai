"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { NODE_ICONS } from "./WorkflowNodeIcons";
import WorkflowSelectionRing from "./WorkflowSelectionRing";
import WorkflowEdges, { getNodeCenter } from "./WorkflowEdges";
import { WF } from "./workflowLayout";

export const NODE_CONTAINER = WF.W;
export const NODE_D = WF.D;
export const NODE_CENTER = WF.CX;

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 2;
const ZOOM_STEP = 0.15;

const NODE_META = {
  trigger: {
    label: "Trigger",
    accent: "workflow-node-trigger",
    iconBg: "from-emerald-400/20 to-emerald-600/10 text-emerald-700",
    ring: "trigger",
    port: "bg-emerald-500",
  },
  retrieve: {
    label: "Retrieve",
    accent: "workflow-node-retrieve",
    iconBg: "from-sky-400/20 to-sky-600/10 text-sky-700",
    ring: "retrieve",
    port: "bg-sky-500",
  },
  llm: {
    label: "LLM",
    accent: "workflow-node-llm",
    iconBg: "from-violet-400/20 to-violet-600/10 text-violet-700",
    ring: "llm",
    port: "bg-violet-500",
  },
  output: {
    label: "Output",
    accent: "workflow-node-output",
    iconBg: "from-neutral-400/15 to-neutral-600/10 text-neutral-700",
    ring: "output",
    port: "bg-neutral-500",
  },
  transform: {
    label: "Transform",
    accent: "workflow-node-transform",
    iconBg: "from-amber-400/20 to-amber-600/10 text-amber-700",
    ring: "transform",
    port: "bg-amber-500",
  },
  condition: {
    label: "Condition",
    accent: "workflow-node-condition",
    iconBg: "from-rose-400/20 to-rose-600/10 text-rose-700",
    ring: "condition",
    port: "bg-rose-500",
  },
  http: {
    label: "HTTP",
    accent: "workflow-node-http",
    iconBg: "from-cyan-400/20 to-cyan-600/10 text-cyan-700",
    ring: "http",
    port: "bg-cyan-500",
  },
  loop: {
    label: "Loop",
    accent: "workflow-node-loop",
    iconBg: "from-indigo-400/20 to-indigo-600/10 text-indigo-700",
    ring: "loop",
    port: "bg-indigo-500",
  },
  parallel: {
    label: "Parallel",
    accent: "workflow-node-parallel",
    iconBg: "from-fuchsia-400/20 to-fuchsia-600/10 text-fuchsia-700",
    ring: "parallel",
    port: "bg-fuchsia-500",
  },
  human: {
    label: "Human",
    accent: "workflow-node-human",
    iconBg: "from-orange-400/20 to-orange-600/10 text-orange-700",
    ring: "human",
    port: "bg-orange-500",
  },
  agent: {
    label: "Agent",
    accent: "workflow-node-agent",
    iconBg: "from-lime-400/20 to-lime-600/10 text-lime-800",
    ring: "agent",
    port: "bg-lime-600",
  },
  subgraph: {
    label: "Subgraph",
    accent: "workflow-node-subgraph",
    iconBg: "from-teal-400/20 to-teal-600/10 text-teal-700",
    ring: "subgraph",
    port: "bg-teal-500",
  },
};

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n));
}

function nodeSubtitle(node) {
  if (node.type === "llm") return node.data?.prompt?.slice(0, 28) || "Set prompt";
  if (node.type === "retrieve") {
    return node.data?.knowledge_id ? `KB #${node.data.knowledge_id}` : "Link knowledge";
  }
  if (node.type === "transform") return node.data?.template?.slice(0, 28) || "Template";
  if (node.type === "condition") return node.data?.keyword || "Keyword match";
  if (node.type === "http") return node.data?.url?.slice(0, 28) || "Request URL";
  if (node.type === "loop") return `max ${node.data?.max || 5} items`;
  if (node.type === "parallel") return `${(node.data?.branches || []).length || 3} branches`;
  if (node.type === "human") return node.data?.require_approval ? "Approval gate" : "Review";
  if (node.type === "agent") return (node.data?.tools || []).join(", ") || "Tools";
  if (node.type === "subgraph") return node.data?.workflow_id ? `WF ${node.data.workflow_id.slice(0, 8)}` : "Link workflow";
  return node.data?.label || node.type;
}

export default function WorkflowCanvas({
  graph,
  onChange,
  selectedId,
  onSelect,
  flowing = false,
  readOnly = false,
}) {
  const viewportRef = useRef(null);
  const didFitRef = useRef(false);
  const [dragging, setDragging] = useState(null);
  const [panning, setPanning] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const editable = Boolean(onChange) && !readOnly;

  const nodeMap = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);

  const nodeMetaMap = useMemo(
    () => Object.fromEntries(nodes.map((n) => [n.id, NODE_META[n.type] || NODE_META.output])),
    [nodes]
  );

  const connectedIds = useMemo(() => {
    const set = new Set();
    edges.forEach((e) => {
      if (selectedId === e.from || selectedId === e.to) {
        set.add(e.from);
        set.add(e.to);
      }
    });
    return set;
  }, [edges, selectedId]);

  const canvasSize = useMemo(() => {
    const padding = 240;
    const minW = 960;
    const minH = 640;
    if (!nodes.length) return { width: minW, height: minH };
    let maxX = 0;
    let maxY = 0;
    nodes.forEach((n) => {
      maxX = Math.max(maxX, (n.x || 0) + WF.W + padding);
      maxY = Math.max(maxY, (n.y || 0) + WF.TOTAL_H + padding);
    });
    return {
      width: Math.max(minW, maxX),
      height: Math.max(minH, maxY),
    };
  }, [nodes]);

  const screenToWorld = useCallback(
    (clientX, clientY) => {
      const rect = viewportRef.current?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return {
        x: (clientX - rect.left - pan.x) / zoom,
        y: (clientY - rect.top - pan.y) / zoom,
      };
    },
    [pan.x, pan.y, zoom]
  );

  const updateNode = useCallback(
    (id, patch) => {
      if (!onChange) return;
      onChange({
        ...graph,
        nodes: nodes.map((n) =>
          n.id === id ? { ...n, ...patch, data: { ...n.data, ...(patch.data || {}) } } : n
        ),
      });
    },
    [graph, nodes, onChange]
  );

  const fitView = useCallback(() => {
    const el = viewportRef.current;
    if (!el || !nodes.length) {
      setZoom(1);
      setPan({ x: 0, y: 0 });
      return;
    }
    const rect = el.getBoundingClientRect();
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    nodes.forEach((n) => {
      minX = Math.min(minX, n.x || 0);
      minY = Math.min(minY, n.y || 0);
      maxX = Math.max(maxX, (n.x || 0) + WF.W);
      maxY = Math.max(maxY, (n.y || 0) + WF.TOTAL_H);
    });
    const pad = 56;
    const contentW = maxX - minX + pad * 2;
    const contentH = maxY - minY + pad * 2;
    const newZoom = clamp(Math.min(rect.width / contentW, rect.height / contentH), ZOOM_MIN, 1.25);
    setZoom(newZoom);
    setPan({
      x: (rect.width - contentW * newZoom) / 2 - minX * newZoom + pad * newZoom,
      y: (rect.height - contentH * newZoom) / 2 - minY * newZoom + pad * newZoom,
    });
  }, [nodes]);

  useEffect(() => {
    if (nodes.length && !didFitRef.current) {
      didFitRef.current = true;
      requestAnimationFrame(() => fitView());
    }
  }, [nodes.length, fitView]);

  function changeZoom(delta) {
    const el = viewportRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    setZoom((prev) => {
      const next = clamp(prev + delta, ZOOM_MIN, ZOOM_MAX);
      const scale = next / prev;
      setPan((p) => ({
        x: cx - (cx - p.x) * scale,
        y: cy - (cy - p.y) * scale,
      }));
      return next;
    });
  }

  function onViewportWheel(e) {
    e.preventDefault();
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
    setZoom((prev) => {
      const next = clamp(prev + delta, ZOOM_MIN, ZOOM_MAX);
      const scale = next / prev;
      setPan((p) => ({
        x: mx - (mx - p.x) * scale,
        y: my - (my - p.y) * scale,
      }));
      return next;
    });
  }

  function onPointerDown(e, node) {
    if (!editable) return;
    e.preventDefault();
    e.stopPropagation();
    const world = screenToWorld(e.clientX, e.clientY);
    setDragging({
      id: node.id,
      ox: world.x - node.x,
      oy: world.y - node.y,
    });
    onSelect(node.id);
  }

  function onPanStart(e) {
    if (!editable) return;
    const canPan = e.button === 1 || (e.button === 0 && e.shiftKey);
    if (!canPan) return;
    e.preventDefault();
    setPanning({ ox: e.clientX - pan.x, oy: e.clientY - pan.y });
  }

  function onPointerMove(e) {
    if (panning) {
      setPan({ x: e.clientX - panning.ox, y: e.clientY - panning.oy });
      return;
    }
    if (!dragging) return;
    const world = screenToWorld(e.clientX, e.clientY);
    updateNode(dragging.id, {
      x: world.x - dragging.ox,
      y: world.y - dragging.oy,
    });
  }

  function onPointerUp() {
    setDragging(null);
    setPanning(null);
  }

  return (
    <div
      ref={viewportRef}
      className={`workflow-studio-canvas relative h-full min-h-[520px] w-full overflow-hidden ${
        flowing ? "workflow-canvas-flowing" : ""
      } ${panning ? "cursor-grabbing" : ""}`}
      onWheel={onViewportWheel}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
      onPointerDown={onPanStart}
      onClick={() => onSelect(null)}
    >
      <div className="workflow-canvas-vignette pointer-events-none absolute inset-0 z-[1]" aria-hidden />
      <div className="workflow-canvas-grid pointer-events-none absolute inset-0 z-[1]" aria-hidden />

      {/* Zoom toolbar */}
      <div className="workflow-canvas-toolbar absolute right-4 top-4 z-50 flex items-center gap-1 rounded-xl border border-white/80 bg-white/90 p-1 shadow-lg backdrop-blur-md">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            changeZoom(-ZOOM_STEP);
          }}
          className="workflow-canvas-toolbar-btn"
          title="Zoom out"
          aria-label="Zoom out"
        >
          −
        </button>
        <span className="min-w-[3rem] px-1 text-center text-[11px] font-semibold tabular-nums text-neutral-600">
          {Math.round(zoom * 100)}%
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            changeZoom(ZOOM_STEP);
          }}
          className="workflow-canvas-toolbar-btn"
          title="Zoom in"
          aria-label="Zoom in"
        >
          +
        </button>
        <span className="mx-0.5 h-5 w-px bg-neutral-200" />
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            fitView();
          }}
          className="workflow-canvas-toolbar-btn !px-2.5 text-[10px] font-semibold"
          title="Fit all nodes in view"
        >
          Fit
        </button>
      </div>

      {editable && (
        <div className="pointer-events-none absolute left-4 top-4 z-50 max-w-[220px] rounded-xl border border-white/80 bg-white/85 px-3 py-2 text-[10px] leading-relaxed text-neutral-600 backdrop-blur-md">
          <strong className="font-semibold">Tip:</strong> link nodes in the Configure panel
          (Connect from / Connect to). Shift+drag to pan · scroll to zoom.
        </div>
      )}

      <div
        className="absolute left-0 top-0 origin-top-left"
        style={{
          width: canvasSize.width,
          height: canvasSize.height,
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
        }}
      >
        <WorkflowEdges
          edges={edges}
          nodeMap={nodeMap}
          selectedId={selectedId}
          nodeMeta={nodeMetaMap}
          flowing={flowing}
        />

        {nodes.map((node) => {
          const meta = NODE_META[node.type] || NODE_META.output;
          const Icon = NODE_ICONS[node.type] || NODE_ICONS.output;
          const isSelected = node.id === selectedId;
          const isConnected = connectedIds.has(node.id);
          const isDragging = dragging?.id === node.id;

          return (
            <div
              key={node.id}
              className="absolute"
              style={{ left: node.x, top: node.y, width: WF.W, height: WF.TOTAL_H }}
              onClick={(e) => e.stopPropagation()}
            >
              <AnimatePresence>
                {isSelected && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.88 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.92 }}
                    transition={{ type: "spring", stiffness: 380, damping: 26 }}
                    className="pointer-events-none absolute left-1/2 z-0 -translate-x-1/2 -translate-y-1/2"
                    style={{ top: WF.CY, width: WF.RING, height: WF.RING }}
                  >
                    <WorkflowSelectionRing type={meta.ring} size={WF.RING} />
                  </motion.div>
                )}
              </AnimatePresence>

              <motion.button
                type="button"
                onPointerDown={(e) => onPointerDown(e, node)}
                animate={{
                  scale: isSelected ? 1.08 : isDragging ? 1.05 : isConnected ? 1.02 : 1,
                  y: isSelected ? -3 : 0,
                }}
                transition={{ type: "spring", stiffness: 420, damping: 28 }}
                className={`workflow-node-circle ${meta.accent} absolute left-1/2 z-10 flex -translate-x-1/2 cursor-grab flex-col items-center justify-center rounded-full border-2 shadow-lg active:cursor-grabbing ${
                  isDragging ? "z-30" : isSelected ? "z-20" : "z-10"
                } ${isConnected && !isSelected ? "workflow-node-connected" : ""}`}
                style={{ top: WF.CY - WF.R, width: WF.D, height: WF.D }}
              >
                <span
                  className={`flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br ${meta.iconBg} ring-1 ring-white/60`}
                >
                  <Icon size={22} />
                </span>
                {isConnected && !isSelected && (
                  <span className="workflow-node-connected-ring pointer-events-none absolute inset-0 rounded-full" />
                )}
              </motion.button>

              <motion.div
                animate={{ opacity: isSelected ? 1 : 0.88, y: isSelected ? -2 : 0 }}
                className="absolute left-1/2 w-[130px] -translate-x-1/2 text-center"
                style={{ top: WF.CY + WF.R + 10 }}
              >
                <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-neutral-400">{meta.label}</p>
                <p className="mt-0.5 truncate text-xs font-semibold text-neutral-900">{nodeSubtitle(node)}</p>
              </motion.div>
            </div>
          );
        })}
      </div>

      {nodes.length === 0 && (
        <div className="pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center gap-3">
          <div className="relative flex h-20 w-20 items-center justify-center">
            <div className="absolute inset-0 animate-pulse rounded-full border-2 border-dashed border-neutral-300/70" />
            <div className="h-10 w-10 rounded-full bg-white/90 shadow-inner" />
          </div>
          <p className="text-sm font-semibold text-neutral-600">Empty pipeline</p>
          <p className="text-xs text-neutral-400">Add nodes from the sidebar, then connect them</p>
        </div>
      )}

      {edges.length > 0 && (
        <motion.div
          animate={flowing ? { scale: [1, 1.02, 1] } : {}}
          transition={{ duration: 1.2, repeat: flowing ? Infinity : 0 }}
          className={`pointer-events-none absolute bottom-4 left-4 z-50 flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-semibold backdrop-blur-md ${
            flowing
              ? "border-emerald-300/70 bg-emerald-50/85 text-emerald-700"
              : "border-white/80 bg-white/80 text-neutral-500"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              flowing ? "bg-emerald-500 workflow-flow-indicator-fast" : "bg-neutral-700 workflow-flow-indicator"
            }`}
          />
          {flowing ? "Running pipeline…" : `${edges.length} connection${edges.length !== 1 ? "s" : ""} · live flow`}
        </motion.div>
      )}
    </div>
  );
}

export { NODE_META, nodeSubtitle, getNodeCenter };
