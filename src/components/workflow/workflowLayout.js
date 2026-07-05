/** Shared node geometry — keep canvas, edges, and ports in sync */
export const WF = {
  W: 176,
  LABEL_H: 44,
  D: 100,
  R: 50,
  CX: 88,
  CY: 90,
  RING: 178,
};

WF.TOTAL_H = WF.CY + WF.R + WF.LABEL_H + 10;

export function nodeCenter(node) {
  return {
    cx: node.x + WF.CX,
    cy: node.y + WF.CY,
  };
}

/** Attach line at the circle edge, pointing toward the other node */
export function portPoints(from, to, radius = WF.R) {
  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;
  const dist = Math.hypot(dx, dy) || 1;
  const nx = dx / dist;
  const ny = dy / dist;
  return {
    sx: from.cx + nx * radius,
    sy: from.cy + ny * radius,
    ex: to.cx - nx * radius,
    ey: to.cy - ny * radius,
    nx,
    ny,
  };
}

export function edgePath(sx, sy, ex, ey) {
  const dx = ex - sx;
  const dy = ey - sy;
  const dist = Math.hypot(dx, dy) || 1;
  const horiz = Math.abs(dx) / dist;
  const curvature = Math.max(36, Math.min(96, Math.abs(dx) * 0.36 + Math.abs(dy) * 0.1));
  const c1x = sx + curvature * horiz + (dy / dist) * 8;
  const c1y = sy + (dy / dist) * curvature * 0.12;
  const c2x = ex - curvature * horiz - (dy / dist) * 8;
  const c2y = ey - (dy / dist) * curvature * 0.12;
  return `M ${sx} ${sy} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${ex} ${ey}`;
}

export function buildPortVisibility(edges) {
  const hasIn = new Set();
  const hasOut = new Set();
  edges.forEach((e) => {
    hasOut.add(e.from);
    hasIn.add(e.to);
  });
  return { hasIn, hasOut };
}
