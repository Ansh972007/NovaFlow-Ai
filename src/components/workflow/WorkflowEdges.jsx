"use client";

import { WF, nodeCenter, portPoints, edgePath } from "./workflowLayout";

const EDGE_DARK = {
  trigger: { line: "#047857", packet: "#10b981" },
  retrieve: { line: "#0369a1", packet: "#0ea5e9" },
  llm: { line: "#6d28d9", packet: "#8b5cf6" },
  output: { line: "#3f3f3f", packet: "#737373" },
};

export function getNodeCenter(node, _legacy) {
  return nodeCenter(node);
}

export default function WorkflowEdges({
  edges,
  nodeMap,
  selectedId,
  nodeMeta,
  flowing = false,
}) {
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible">
      {edges.map((e, i) => {
        const from = nodeMap[e.from];
        const to = nodeMap[e.to];
        if (!from || !to) return null;

        const fromC = nodeCenter(from);
        const toC = nodeCenter(to);
        const { sx, sy, ex, ey } = portPoints(fromC, toC);
        const d = edgePath(sx, sy, ex, ey);
        const selected = selectedId && (selectedId === e.from || selectedId === e.to);
        const hot = flowing || selected;
        const fromType = nodeMeta[from.id]?.ring || from.type || "output";
        const dark = EDGE_DARK[fromType] || EDGE_DARK.output;
        const delay = `${i * 0.2}s`;
        const dur = flowing ? "1.15s" : hot ? "1.9s" : "3.4s";
        const dashClass = flowing ? "wf-edge-dash-flowing" : hot ? "wf-edge-dash-active" : "wf-edge-dash-idle";

        return (
          <g key={`${e.from}-${e.to}`}>
            <path
              d={d}
              fill="none"
              stroke={dark.line}
              strokeWidth={hot ? 2.75 : 2.25}
              strokeLinecap="round"
              strokeDasharray={hot ? "11 7" : "9 7"}
              className={dashClass}
              style={{ "--wf-edge-delay": delay }}
            />

            {/* Data packet: source → next node */}
            <circle r={hot ? 3.5 : 3} fill={dark.packet} className="wf-edge-packet">
              <animateMotion dur={dur} repeatCount="indefinite" path={d} begin={delay} />
            </circle>
            <circle r="1.75" fill="#fff" opacity="0.9">
              <animateMotion dur={dur} repeatCount="indefinite" path={d} begin={delay} />
            </circle>

            {/* Second packet — staggered for continuous flow feel */}
            <circle r="2.5" fill={dark.packet} opacity="0.55">
              <animateMotion dur={dur} repeatCount="indefinite" path={d} begin={`${i * 0.2 + 0.55}s`} />
            </circle>
          </g>
        );
      })}
    </svg>
  );
}

export { WF as NODE_LAYOUT, EDGE_DARK };
