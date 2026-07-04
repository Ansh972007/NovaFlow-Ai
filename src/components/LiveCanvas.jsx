"use client";

import { useEffect, useRef } from "react";

function rand(min, max) {
  return Math.random() * (max - min) + min;
}

export default function LiveCanvas({ variant = "light", mouseTracking = true, tone = "neutral" }) {
  const canvasRef = useRef(null);
  const mouseRef = useRef({ x: -9999, y: -9999 });
  const frameRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const isDark = variant === "dark";
    const isSubtle = variant === "subtle";

    let w = 0;
    let h = 0;
    let nodes = [];
    let pulses = [];

    const isViolet = tone === "violet";

    const density = isDark && isViolet ? 0.000055 : isViolet ? 0.000042 : isSubtle ? 0.00005 : 0.00008;
    const maxDist = isDark && isViolet ? 175 : isViolet ? 155 : isSubtle ? 160 : 210;
    const nodeCount = () => Math.min(100, Math.max(40, Math.floor(w * h * density)));

    function palette() {
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
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.offsetWidth;
      h = canvas.offsetHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
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
      const colors = palette();
      ctx.clearRect(0, 0, w, h);

      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        n.phase += 0.025;

        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;

        if (mouseTracking && mx > 0) {
          const dx = mx - n.x;
          const dy = my - n.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 280) {
            const force = (280 - dist) / 280;
            n.vx -= (dx / dist) * force * 0.035;
            n.vy -= (dy / dist) * force * 0.035;
          }
          if (dist < 120) {
            n.vx += (dx / dist) * 0.008;
            n.vy += (dy / dist) * 0.008;
          }
        }

        n.vx *= 0.998;
        n.vy *= 0.998;
      }

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist > maxDist) continue;

          const alpha = 1 - dist / maxDist;
          const nearMouse =
            mouseTracking &&
            mx > 0 &&
            (Math.hypot(mx - a.x, my - a.y) < 200 ||
              Math.hypot(mx - b.x, my - b.y) < 200);

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
        const near =
          mouseTracking && mx > 0 && Math.hypot(mx - n.x, my - n.y) < 180;
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

      frameRef.current = requestAnimationFrame(draw);
    }

    const onMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    const onLeave = () => {
      mouseRef.current = { x: -9999, y: -9999 };
    };

    resize();
    draw();

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    if (mouseTracking) {
      window.addEventListener("mousemove", onMove, { passive: true });
      window.addEventListener("mouseleave", onLeave);
    }

    return () => {
      cancelAnimationFrame(frameRef.current);
      ro.disconnect();
      if (mouseTracking) {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseleave", onLeave);
      }
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
