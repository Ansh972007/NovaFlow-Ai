"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { NODE_ICONS } from "./WorkflowNodeIcons";
import WorkflowSelectionRing from "./WorkflowSelectionRing";
import WorkflowEdges, { getNodeCenter } from "./WorkflowEdges";
import { WF, buildPortVisibility } from "./workflowLayout";

export const NODE_CONTAINER = WF.W;
export const NODE_D = WF.D;
export const NODE_CENTER = WF.CX;

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
};

function nodeSubtitle(node) {
  if (node.type === "llm") return node.data?.prompt?.slice(0, 28) || "Set prompt";
  if (node.type === "retrieve") {
    return node.data?.knowledge_id ? `KB #${node.data.knowledge_id}` : "Link knowledge";
  }
  if (node.type === "transform") return node.data?.template?.slice(0, 28) || "Template";
  if (node.type === "condition") return node.data?.keyword || "Keyword match";
  if (node.type === "http") return node.data?.url?.slice(0, 28) || "Request URL";
  return node.data?.label || node.type;
}

export default function WorkflowCanvas({ graph, onChange, selectedId, onSelect, flowing = false }) {
  const canvasRef = useRef(null);
  const [dragging, setDragging] = useState(null);

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const nodeMap = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);

  const nodeMetaMap = useMemo(
    () => Object.fromEntries(nodes.map((n) => [n.id, NODE_META[n.type] || NODE_META.output])),
    [nodes]
  );

  const portVisibility = useMemo(() => buildPortVisibility(edges), [edges]);

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

  const updateNode = useCallback(
    (id, patch) => {
      onChange({
        ...graph,
        nodes: nodes.map((n) =>
          n.id === id ? { ...n, ...patch, data: { ...n.data, ...(patch.data || {}) } } : n
        ),
      });
    },
    [graph, nodes, onChange]
  );

  function onPointerDown(e, node) {
    e.preventDefault();
    e.stopPropagation();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    setDragging({
      id: node.id,
      ox: e.clientX - rect.left - node.x,
      oy: e.clientY - rect.top - node.y,
    });
    onSelect(node.id);
  }

  function onPointerMove(e) {
    if (!dragging || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.max(8, Math.min(rect.width - WF.W - 8, e.clientX - rect.left - dragging.ox));
    const y = Math.max(8, Math.min(rect.height - WF.TOTAL_H - 8, e.clientY - rect.top - dragging.oy));
    updateNode(dragging.id, { x, y });
  }

  function onPointerUp() {
    setDragging(null);
  }

  return (
    <div
      ref={canvasRef}
      className={`workflow-studio-canvas relative h-full min-h-[520px] w-full overflow-hidden ${
        flowing ? "workflow-canvas-flowing" : ""
      }`}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
      onClick={() => onSelect(null)}
    >
      <div className="workflow-canvas-vignette pointer-events-none absolute inset-0" aria-hidden />
      <div className="workflow-canvas-grid pointer-events-none absolute inset-0" aria-hidden />

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
        const live = isSelected || isConnected || flowing;

        const showIn = portVisibility.hasIn.has(node.id);
        const showOut = portVisibility.hasOut.has(node.id);

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

            {showOut && (
              <span
                className={`workflow-node-port ${meta.port} ${live ? "workflow-node-port-live" : ""}`}
                style={{ left: WF.CX + WF.R - 4, top: WF.CY - 4 }}
                aria-hidden
              />
            )}
            {showIn && (
              <span
                className={`workflow-node-port ${meta.port} ${live ? "workflow-node-port-live" : ""}`}
                style={{ left: WF.CX - WF.R - 4, top: WF.CY - 4 }}
                aria-hidden
              />
            )}

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

      {nodes.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-3">
          <div className="relative flex h-20 w-20 items-center justify-center">
            <div className="absolute inset-0 animate-pulse rounded-full border-2 border-dashed border-neutral-300/70" />
            <div className="h-10 w-10 rounded-full bg-white/90 shadow-inner" />
          </div>
          <p className="text-sm font-semibold text-neutral-600">Empty pipeline</p>
          <p className="text-xs text-neutral-400">Nodes appear here from your template</p>
        </div>
      )}

      {edges.length > 0 && (
        <motion.div
          animate={flowing ? { scale: [1, 1.02, 1] } : {}}
          transition={{ duration: 1.2, repeat: flowing ? Infinity : 0 }}
          className={`pointer-events-none absolute bottom-4 left-4 flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-semibold backdrop-blur-md ${
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
