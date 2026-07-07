"use client";

import { memo, useEffect, useRef } from "react";
import { getPointer } from "@/lib/runtime/pointerBus";
import { isPageVisible, subscribeVisibility } from "@/lib/runtime/pageVisibility";
import { subscribeAnimationFrame } from "@/lib/runtime/rafLoop";

function rand(min, max) {
  return Math.random() * (max - min) + min;
}

function palette(variant, tone) {
  const isDark = variant === "dark";
  const isViolet = tone === "violet";

  if (isDark && isViolet) {
    return {
      node: "rgba(196,181,253,0.95)",
      nodeGlow: "rgba(139,92,246,0.38)",
      line: "rgba(139,92,246,0.22)",
      lineBright: "rgba(167,139,250,0.68)",
      pulse: "rgba(224,231,255,0.95)",
      cursor: "rgba(139,92,246,0.28)",
    };
  }
  if (isDark) {
    return {
      node: "rgba(255,255,255,0.75)",
      nodeGlow: "rgba(255,255,255,0.2)",
      line: "rgba(255,255,255,0.12)",
      lineBright: "rgba(255,255,255,0.45)",
      pulse: "rgba(255,255,255,0.95)",
      cursor: "rgba(255,255,255,0.12)",
    };
  }
  if (isViolet) {
    return {
      node: "rgba(91,33,182,0.5)",
      nodeGlow: "rgba(139,92,246,0.16)",
      line: "rgba(99,102,241,0.11)",
      lineBright: "rgba(124,58,237,0.32)",
      pulse: "rgba(91,33,182,0.8)",
      cursor: "rgba(139,92,246,0.11)",
    };
  }
  return {
    node: "rgba(10,10,10,0.55)",
    nodeGlow: "rgba(10,10,10,0.12)",
    line: "rgba(10,10,10,0.1)",
    lineBright: "rgba(10,10,10,0.28)",
    pulse: "rgba(10,10,10,0.85)",
    cursor: "rgba(0,0,0,0.08)",
  };
}

function LiveCanvas({ variant = "light", mouseTracking = true, tone = "neutral" }) {
  const canvasRef = useRef(null);
  const canvasRectRef = useRef({ left: 0, top: 0, width: 0, height: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    const isDark = variant === "dark";
    const isSubtle = variant === "subtle";
    const isViolet = tone === "violet";
    const colors = palette(variant, tone);

    const density = isDark && isViolet ? 0.000055 : isViolet ? 0.000042 : isSubtle ? 0.00005 : 0.00008;
    const maxDist = isDark && isViolet ? 175 : isViolet ? 155 : isSubtle ? 160 : 210;
    const maxDistSq = maxDist * maxDist;
    const cellSize = maxDist;

    let w = 0;
    let h = 0;
    let nodes = [];
    let pulses = [];
    let running = isPageVisible();
    let gridCols = 1;
    let gridRows = 1;
    let buckets = [];

    function ensureGrid() {
      gridCols = Math.max(1, Math.ceil(w / cellSize));
      gridRows = Math.max(1, Math.ceil(h / cellSize));
      const size = gridCols * gridRows;
      if (buckets.length !== size) {
        buckets = Array.from({ length: size }, () => []);
      }
    }

    function clearGrid() {
      for (let i = 0; i < buckets.length; i++) buckets[i].length = 0;
    }

    function cellIndex(x, y) {
      const cx = Math.min(gridCols - 1, Math.max(0, Math.floor(x / cellSize)));
      const cy = Math.min(gridRows - 1, Math.max(0, Math.floor(y / cellSize)));
      return cy * gridCols + cx;
    }

    const nodeCount = () => Math.min(100, Math.max(40, Math.floor(w * h * density)));

    function initNodes() {
      const count = nodeCount();
      nodes = Array.from({ length: count }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        vx: rand(-0.3, 0.3),
        vy: rand(-0.3, 0.3),
        r: rand(1.5, 3.2),
        phase: rand(0, Math.PI * 2),
      }));
      pulses = [];
      ensureGrid();
    }

    function updateCanvasRect() {
      const rect = canvas.getBoundingClientRect();
      canvasRectRef.current = {
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
      };
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.offsetWidth;
      h = canvas.offsetHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      updateCanvasRect();
      initNodes();
    }

    function spawnPulse(a, b, boosted) {
      if (pulses.length > 50) return;
      if (Math.random() > (boosted ? 0.04 : 0.022)) return;
      pulses.push({
        ax: nodes[a].x,
        ay: nodes[a].y,
        bx: nodes[b].x,
        by: nodes[b].y,
        t: 0,
        speed: rand(0.012, 0.025),
      });
    }

    function draw() {
      if (!running) return;

      ctx.clearRect(0, 0, w, h);

      const { clientX, clientY, active: pointerActive } = getPointer();
      const rect = canvasRectRef.current;
      const mx = mouseTracking && pointerActive ? clientX - rect.left : -9999;
      const my = mouseTracking && pointerActive ? clientY - rect.top : -9999;

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        n.phase += 0.025;

        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;

        if (mouseTracking && mx > 0) {
          const dx = mx - n.x;
          const dy = my - n.y;
          const distSq = dx * dx + dy * dy;
          if (distSq < 78400 && distSq > 1) {
            const dist = Math.sqrt(distSq);
            const force = (280 - dist) / 280;
            n.vx -= (dx / dist) * force * 0.035;
            n.vy -= (dy / dist) * force * 0.035;
          }
          if (distSq < 14400) {
            const dist = Math.sqrt(distSq);
            n.vx += (dx / dist) * 0.008;
            n.vy += (dy / dist) * 0.008;
          }
        }

        n.vx *= 0.998;
        n.vy *= 0.998;
      }

      clearGrid();
      for (let i = 0; i < nodes.length; i++) {
        buckets[cellIndex(nodes[i].x, nodes[i].y)].push(i);
      }

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        const acx = Math.floor(a.x / cellSize);
        const acy = Math.floor(a.y / cellSize);

        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const ncx = acx + dx;
            const ncy = acy + dy;
            if (ncx < 0 || ncy < 0 || ncx >= gridCols || ncy >= gridRows) continue;

            const bucket = buckets[ncy * gridCols + ncx];
            for (let bi = 0; bi < bucket.length; bi++) {
              const j = bucket[bi];
              if (j <= i) continue;

              const b = nodes[j];
              const ddx = a.x - b.x;
              const ddy = a.y - b.y;
              const distSq = ddx * ddx + ddy * ddy;
              if (distSq > maxDistSq) continue;

              const dist = Math.sqrt(distSq);
              const alpha = 1 - dist / maxDist;
              let nearMouse = false;
              if (mouseTracking && mx > 0) {
                const dax = mx - a.x;
                const day = my - a.y;
                const dbx = mx - b.x;
                const dby = my - b.y;
                nearMouse = dax * dax + day * day < 40000 || dbx * dbx + dby * dby < 40000;
              }

              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.lineTo(b.x, b.y);
              ctx.strokeStyle = nearMouse ? colors.lineBright : colors.line;
              ctx.globalAlpha = alpha * (nearMouse ? 1 : 0.75);
              ctx.lineWidth = nearMouse ? 1.8 : 0.8;
              ctx.stroke();
              ctx.globalAlpha = 1;

              spawnPulse(i, j, nearMouse);
            }
          }
        }
      }

      for (const p of pulses) {
        p.t += p.speed;
        if (p.t > 1) continue;
        const px = p.ax + (p.bx - p.ax) * p.t;
        const py = p.ay + (p.by - p.ay) * p.t;
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = colors.pulse;
        ctx.globalAlpha = 1 - Math.abs(p.t - 0.5) * 1.8;
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      pulses = pulses.filter((p) => p.t <= 1);

      for (const n of nodes) {
        const dx = mx - n.x;
        const dy = my - n.y;
        const near = mouseTracking && mx > 0 && dx * dx + dy * dy < 32400;
        const pulse = 0.65 + Math.sin(n.phase) * 0.35;

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * pulse + (near ? 5 : 3), 0, Math.PI * 2);
        ctx.fillStyle = colors.nodeGlow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * pulse * (near ? 1.2 : 1), 0, Math.PI * 2);
        ctx.fillStyle = colors.node;
        ctx.fill();
      }

      if (mouseTracking && mx > 0) {
        const grad = ctx.createRadialGradient(mx, my, 0, mx, my, 280);
        grad.addColorStop(0, colors.cursor);
        grad.addColorStop(0.4, isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)");
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);

        ctx.beginPath();
        ctx.arc(mx, my, 4, 0, Math.PI * 2);
        ctx.fillStyle = isDark
          ? isViolet
            ? "rgba(167,139,250,0.65)"
            : "rgba(255,255,255,0.5)"
          : isViolet
            ? "rgba(124,58,237,0.4)"
            : "rgba(0,0,0,0.25)";
        ctx.fill();
      }
    }

    let unsubFrame = null;

    const unsubVisibility = subscribeVisibility((visible) => {
      running = visible;
      if (visible) {
        if (!unsubFrame) unsubFrame = subscribeAnimationFrame(draw);
      } else if (unsubFrame) {
        unsubFrame();
        unsubFrame = null;
      }
    });

    resize();
    unsubFrame = subscribeAnimationFrame(draw);

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    return () => {
      if (unsubFrame) unsubFrame();
      unsubVisibility();
      ro.disconnect();
    };
  }, [variant, mouseTracking, tone]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 h-full w-full"
      aria-hidden
    />
  );
}

export default memo(LiveCanvas);
