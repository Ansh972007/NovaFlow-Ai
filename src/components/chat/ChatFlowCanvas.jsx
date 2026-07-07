"use client";

import { memo, useEffect, useRef } from "react";
import { getPointer, subscribePointer } from "@/lib/runtime/pointerBus";
import { isPageVisible, subscribeVisibility } from "@/lib/runtime/pageVisibility";
import { subscribeAnimationFrame } from "@/lib/runtime/rafLoop";

function rand(min, max) {
  return Math.random() * (max - min) + min;
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function ChatFlowCanvas({ active = false }) {
  const canvasRef = useRef(null);
  const smoothRef = useRef({ x: -9999, y: -9999 });
  const activeRef = useRef(active);
  const parentRectRef = useRef({ left: 0, top: 0, width: 0, height: 0 });

  useEffect(() => {
    activeRef.current = active;
  }, [active]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    let w = 0;
    let h = 0;
    let nodes = [];
    let streams = [];
    let pulses = [];
    let ripples = [];
    let running = isPageVisible();
    let gridCols = 1;
    let gridRows = 1;
    let buckets = [];
    let lastRipple = 0;

    const maxDist = 195;
    const maxDistSq = maxDist * maxDist;
    const cellSize = maxDist;

    const colors = {
      node: "rgba(10,10,10,0.62)",
      nodeGlow: "rgba(10,10,10,0.16)",
      line: "rgba(10,10,10,0.11)",
      lineBright: "rgba(10,10,10,0.34)",
      pulse: "rgba(10,10,10,0.9)",
      stream: "rgba(10,10,10,0.22)",
      streamBright: "rgba(10,10,10,0.45)",
      cursor: "rgba(0,0,0,0.1)",
    };

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

    function fieldAt(x, y, t, mx, my) {
      let ax =
        Math.sin(y * 0.0055 + t * 0.9) * 0.55 +
        Math.cos(x * 0.004 - t * 0.55) * 0.45;
      let ay =
        Math.cos(x * 0.0055 + t * 0.65) * 0.55 -
        Math.sin(y * 0.0045 + t * 0.45) * 0.4;

      if (mx > 0 && my > 0) {
        const dx = mx - x;
        const dy = my - y;
        const distSq = dx * dx + dy * dy;
        if (distSq < 78400 && distSq > 1) {
          const dist = Math.sqrt(distSq);
          const force = (280 - dist) / 280;
          ax += (-dy / dist) * force * 1.35;
          ay += (dx / dist) * force * 1.35;
          ax += (dx / dist) * force * 0.25;
          ay += (dy / dist) * force * 0.25;
        }
      }

      const mag = Math.hypot(ax, ay) || 1;
      return { ax: ax / mag, ay: ay / mag };
    }

    function getPerfScale() {
      const cores = navigator.hardwareConcurrency || 8;
      const mem = navigator.deviceMemory || 8;
      if (window.innerWidth < 768) return 0.72;
      if (cores <= 4 || mem <= 4) return 0.72;
      if (cores <= 8 || mem <= 8) return 0.86;
      return 1;
    }

    function init() {
      const perfScale = getPerfScale();
      const nodeCount = Math.min(72, Math.max(40, Math.floor(w * h * 0.00007 * perfScale)));
      nodes = Array.from({ length: nodeCount }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        vx: rand(-0.25, 0.25),
        vy: rand(-0.25, 0.25),
        r: rand(1.8, 3.4),
        phase: rand(0, Math.PI * 2),
        orbit: rand(12, 28),
      }));

      const streamCount = Math.min(420, Math.max(220, Math.floor(w * h * 0.00028 * perfScale)));
      streams = Array.from({ length: streamCount }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        speed: rand(0.7, 1.6),
        trail: [],
      }));

      pulses = [];
      ensureGrid();
    }

    function updateParentRect() {
      const parent = canvas.parentElement;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      parentRectRef.current = {
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
      };
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const parent = canvas.parentElement;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      updateParentRect();
      init();
    }

    function spawnPulse(a, b, boosted) {
      if (pulses.length > 60) return;
      if (Math.random() > (boosted ? 0.05 : 0.028)) return;
      const na = nodes[a];
      const nb = nodes[b];
      const mx = (na.x + nb.x) / 2;
      const my = (na.y + nb.y) / 2;
      const perpX = -(nb.y - na.y);
      const perpY = nb.x - na.x;
      const len = Math.hypot(perpX, perpY) || 1;
      pulses.push({
        ax: na.x,
        ay: na.y,
        bx: nb.x,
        by: nb.y,
        cx: mx + (perpX / len) * rand(-40, 40),
        cy: my + (perpY / len) * rand(-40, 40),
        t: 0,
        speed: rand(0.014, 0.028),
      });
    }

    function drawAurora(t, boost) {
      for (let i = 0; i < 3; i++) {
        const y = h * (0.25 + i * 0.22) + Math.sin(t * 0.6 + i * 1.4) * 40;
        const grad = ctx.createLinearGradient(0, y - 80, w, y + 80);
        grad.addColorStop(0, "transparent");
        grad.addColorStop(0.35, `rgba(10,10,10,${(0.018 + i * 0.006) * boost})`);
        grad.addColorStop(0.5, `rgba(10,10,10,${(0.035 + i * 0.008) * boost})`);
        grad.addColorStop(0.65, `rgba(10,10,10,${(0.018 + i * 0.006) * boost})`);
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.fillRect(0, y - 100, w, 200);
      }
    }

    function drawStreams(t, mx, my, boost) {
      const spdMul = activeRef.current ? 1.25 : 1;

      for (const s of streams) {
        const { ax, ay } = fieldAt(s.x, s.y, t, mx, my);
        s.x += ax * s.speed * spdMul;
        s.y += ay * s.speed * spdMul;

        if (s.x < 0) s.x = w;
        else if (s.x > w) s.x = 0;
        if (s.y < 0) s.y = h;
        else if (s.y > h) s.y = 0;

        s.trail.push({ x: s.x, y: s.y });
        if (s.trail.length > 10) s.trail.shift();
      }

      ctx.lineWidth = 0.65;
      ctx.strokeStyle = colors.stream;
      ctx.beginPath();
      let farTrails = false;
      const farAlpha = 0.16 * boost * 0.7;

      for (const s of streams) {
        const dx = mx - s.x;
        const dy = my - s.y;
        const near = mx > 0 && dx * dx + dy * dy < 32400;
        if (near || s.trail.length <= 2) continue;
        ctx.moveTo(s.trail[0].x, s.trail[0].y);
        for (let ti = 1; ti < s.trail.length; ti++) {
          ctx.lineTo(s.trail[ti].x, s.trail[ti].y);
        }
        farTrails = true;
      }
      if (farTrails) {
        ctx.globalAlpha = farAlpha;
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      for (const s of streams) {
        const dx = mx - s.x;
        const dy = my - s.y;
        const near = mx > 0 && dx * dx + dy * dy < 32400;
        const alpha = (near ? 0.38 : 0.16) * boost;

        if (near && s.trail.length > 2) {
          ctx.beginPath();
          ctx.moveTo(s.trail[0].x, s.trail[0].y);
          for (let ti = 1; ti < s.trail.length; ti++) {
            ctx.lineTo(s.trail[ti].x, s.trail[ti].y);
          }
          ctx.strokeStyle = colors.streamBright;
          ctx.globalAlpha = alpha * (0.4 + (s.trail.length / 10) * 0.6);
          ctx.lineWidth = 1.1;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }

        ctx.beginPath();
        ctx.arc(s.x, s.y, near ? 1.4 : 0.9, 0, Math.PI * 2);
        ctx.fillStyle = near ? colors.streamBright : colors.stream;
        ctx.globalAlpha = alpha;
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    }

    function drawNetwork(t, mx, my, boost, pointerActive) {
      for (const n of nodes) {
        n.x += n.vx * (activeRef.current ? 1.15 : 1);
        n.y += n.vy * (activeRef.current ? 1.15 : 1);
        n.phase += 0.022;

        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;

        if (pointerActive && mx > 0) {
          const dx = mx - n.x;
          const dy = my - n.y;
          const distSq = dx * dx + dy * dy;
          if (distSq < 90000 && distSq > 1) {
            const dist = Math.sqrt(distSq);
            const force = (300 - dist) / 300;
            n.vx -= (dx / dist) * force * 0.04;
            n.vy -= (dy / dist) * force * 0.04;
          }
          if (distSq < 16900) {
            const dist = Math.sqrt(distSq);
            n.vx += (dx / dist) * 0.012;
            n.vy += (dy / dist) * 0.012;
          }
        }

        n.vx *= 0.997;
        n.vy *= 0.997;
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
              if (pointerActive && mx > 0) {
                const dax = mx - a.x;
                const day = my - a.y;
                const dbx = mx - b.x;
                const dby = my - b.y;
                nearMouse = dax * dax + day * day < 44100 || dbx * dbx + dby * dby < 44100;
              }

              const mx2 = (a.x + b.x) / 2;
              const my2 = (a.y + b.y) / 2;
              const perpX = -(b.y - a.y);
              const perpY = b.x - a.x;
              const len = Math.hypot(perpX, perpY) || 1;
              const wave = Math.sin(t * 1.8 + i * 0.3 + j * 0.2) * 36;
              const cx = mx2 + (perpX / len) * wave;
              const cy = my2 + (perpY / len) * wave;

              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.quadraticCurveTo(cx, cy, b.x, b.y);
              ctx.strokeStyle = nearMouse ? colors.lineBright : colors.line;
              ctx.globalAlpha = alpha * (nearMouse ? 1 : 0.8) * boost;
              ctx.lineWidth = nearMouse ? 1.6 : 0.85;
              ctx.stroke();
              ctx.globalAlpha = 1;

              spawnPulse(i, j, nearMouse);
            }
          }
        }
      }

      for (const p of pulses) {
        p.t += p.speed * (activeRef.current ? 1.2 : 1);
        if (p.t > 1) continue;

        const u = 1 - p.t;
        const px = u * u * p.ax + 2 * u * p.t * p.cx + p.t * p.t * p.bx;
        const py = u * u * p.ay + 2 * u * p.t * p.cy + p.t * p.t * p.by;

        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fillStyle = colors.pulse;
        ctx.globalAlpha = 1 - Math.abs(p.t - 0.5) * 1.6;
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      pulses = pulses.filter((p) => p.t <= 1);

      for (const n of nodes) {
        const dx = mx - n.x;
        const dy = my - n.y;
        const near = pointerActive && mx > 0 && dx * dx + dy * dy < 40000;
        const pulse = 0.65 + Math.sin(n.phase) * 0.35;

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.orbit * pulse * 0.35 + (near ? 8 : 4), 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(10,10,10,${near ? 0.14 : 0.06})`;
        ctx.lineWidth = 0.75;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * pulse + (near ? 6 : 3.5), 0, Math.PI * 2);
        ctx.fillStyle = colors.nodeGlow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * pulse * (near ? 1.25 : 1), 0, Math.PI * 2);
        ctx.fillStyle = colors.node;
        ctx.fill();
      }
    }

    function drawCursor(mx, my, boost, pointerActive) {
      if (!pointerActive || mx <= 0) return;

      const grad = ctx.createRadialGradient(mx, my, 0, mx, my, 320);
      grad.addColorStop(0, colors.cursor);
      grad.addColorStop(0.35, "rgba(0,0,0,0.04)");
      grad.addColorStop(1, "transparent");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      ctx.beginPath();
      ctx.arc(mx, my, 52, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(10,10,10,0.12)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 8]);
      ctx.lineDashOffset = -performance.now() * 0.03;
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.beginPath();
      ctx.arc(mx, my, 5, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(10,10,10,0.35)";
      ctx.fill();

      ctx.beginPath();
      ctx.arc(mx, my, 2, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(10,10,10,0.75)";
      ctx.fill();
    }

    function render(time) {
      if (!running) return;

      const { clientX, clientY, active: pointerActive } = getPointer();
      const rect = parentRectRef.current;
      const rawX = pointerActive ? clientX - rect.left : -9999;
      const rawY = pointerActive ? clientY - rect.top : -9999;

      const t = time * 0.001;
      const smooth = smoothRef.current;
      smooth.x = lerp(smooth.x, rawX, pointerActive ? 0.14 : 0.05);
      smooth.y = lerp(smooth.y, rawY, pointerActive ? 0.14 : 0.05);
      const mx = smooth.x;
      const my = smooth.y;
      const boost = activeRef.current ? 1.3 : 1;

      ctx.clearRect(0, 0, w, h);

      drawAurora(t, boost);
      drawStreams(t, mx, my, boost);
      drawNetwork(t, mx, my, boost, pointerActive);
      drawCursor(mx, my, boost, pointerActive);

      ripples = ripples.filter((rip) => {
        rip.r += rip.speed;
        rip.alpha *= 0.962;
        if (rip.alpha < 0.008) return false;
        ctx.strokeStyle = `rgba(10,10,10,${rip.alpha})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(rip.x, rip.y, rip.r, 0, Math.PI * 2);
        ctx.stroke();
        return rip.r < Math.max(w, h) * 0.8;
      });
    }

    const onClick = (e) => {
      const rect = parentRectRef.current;
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      ripples.push({ x, y, r: 14, alpha: 0.42, speed: 3.5 });
      ripples.push({ x, y, r: 8, alpha: 0.28, speed: 2.2 });
    };

    const unsubPointer = subscribePointer((cx, cy, pointerActive) => {
      if (!pointerActive) return;
      const rect = parentRectRef.current;
      const now = performance.now();
      if (now - lastRipple > 180) {
        ripples.push({
          x: cx - rect.left,
          y: cy - rect.top,
          r: 10,
          alpha: 0.28,
          speed: 2.8,
        });
        lastRipple = now;
      }
    });

    let unsubFrame = null;

    const unsubVisibility = subscribeVisibility((visible) => {
      running = visible;
      if (visible) {
        if (!unsubFrame) unsubFrame = subscribeAnimationFrame(render);
      } else if (unsubFrame) {
        unsubFrame();
        unsubFrame = null;
      }
    });

    resize();
    unsubFrame = subscribeAnimationFrame(render);

    const ro = new ResizeObserver(resize);
    ro.observe(canvas.parentElement || canvas);
    window.addEventListener("mousedown", onClick);

    return () => {
      if (unsubFrame) unsubFrame();
      unsubPointer();
      unsubVisibility();
      ro.disconnect();
      window.removeEventListener("mousedown", onClick);
    };
  }, []);

  return (
    <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden />
  );
}

export default memo(ChatFlowCanvas);
