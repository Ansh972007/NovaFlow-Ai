"use client";

import { useEffect, useRef } from "react";

function rand(min, max) {
  return Math.random() * (max - min) + min;
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

export default function ChatFlowCanvas({ active = false }) {
  const canvasRef = useRef(null);
  const mouseRef = useRef({ x: -9999, y: -9999, active: false });
  const smoothRef = useRef({ x: -9999, y: -9999 });
  const activeRef = useRef(active);

  useEffect(() => {
    activeRef.current = active;
  }, [active]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let w = 0;
    let h = 0;
    let nodes = [];
    let streams = [];
    let pulses = [];
    let ripples = [];
    let frameId = 0;

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
        const dist = Math.hypot(dx, dy);
        if (dist < 280 && dist > 1) {
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

    function init() {
      const nodeCount = Math.min(72, Math.max(48, Math.floor(w * h * 0.00007)));
      nodes = Array.from({ length: nodeCount }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        vx: rand(-0.25, 0.25),
        vy: rand(-0.25, 0.25),
        r: rand(1.8, 3.4),
        phase: rand(0, Math.PI * 2),
        orbit: rand(12, 28),
      }));

      const streamCount = Math.min(420, Math.max(220, Math.floor(w * h * 0.00028)));
      streams = Array.from({ length: streamCount }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        speed: rand(0.7, 1.6),
        trail: [],
      }));

      pulses = [];
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
      for (const s of streams) {
        const { ax, ay } = fieldAt(s.x, s.y, t, mx, my);
        const spd = s.speed * (activeRef.current ? 1.25 : 1);
        s.x += ax * spd;
        s.y += ay * spd;

        if (s.x < 0) s.x = w;
        if (s.x > w) s.x = 0;
        if (s.y < 0) s.y = h;
        if (s.y > h) s.y = 0;

        s.trail.push({ x: s.x, y: s.y });
        if (s.trail.length > 10) s.trail.shift();

        const near = mx > 0 && Math.hypot(mx - s.x, my - s.y) < 180;
        const alpha = (near ? 0.38 : 0.16) * boost;

        if (s.trail.length > 2) {
          ctx.beginPath();
          ctx.moveTo(s.trail[0].x, s.trail[0].y);
          for (let ti = 1; ti < s.trail.length; ti++) {
            ctx.lineTo(s.trail[ti].x, s.trail[ti].y);
          }
          ctx.strokeStyle = near ? colors.streamBright : colors.stream;
          ctx.globalAlpha = alpha * (0.4 + (s.trail.length / 10) * 0.6);
          ctx.lineWidth = near ? 1.1 : 0.65;
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

    function drawNetwork(t, mx, my, boost) {
      const maxDist = 195;

      for (const n of nodes) {
        n.x += n.vx * (activeRef.current ? 1.15 : 1);
        n.y += n.vy * (activeRef.current ? 1.15 : 1);
        n.phase += 0.022;

        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;

        if (mouseRef.current.active && mx > 0) {
          const dx = mx - n.x;
          const dy = my - n.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 300 && dist > 1) {
            const force = (300 - dist) / 300;
            n.vx -= (dx / dist) * force * 0.04;
            n.vy -= (dy / dist) * force * 0.04;
          }
          if (dist < 130) {
            n.vx += (dx / dist) * 0.012;
            n.vy += (dy / dist) * 0.012;
          }
        }

        n.vx *= 0.997;
        n.vy *= 0.997;
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
            mouseRef.current.active &&
            mx > 0 &&
            (Math.hypot(mx - a.x, my - a.y) < 210 || Math.hypot(mx - b.x, my - b.y) < 210);

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
        const near = mouseRef.current.active && mx > 0 && Math.hypot(mx - n.x, my - n.y) < 200;
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

    function drawCursor(mx, my, boost) {
      if (!mouseRef.current.active || mx <= 0) return;

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
      const t = time * 0.001;
      const raw = mouseRef.current;
      const smooth = smoothRef.current;
      smooth.x = lerp(smooth.x, raw.x, raw.active ? 0.14 : 0.05);
      smooth.y = lerp(smooth.y, raw.y, raw.active ? 0.14 : 0.05);
      const mx = smooth.x;
      const my = smooth.y;
      const boost = activeRef.current ? 1.3 : 1;

      ctx.clearRect(0, 0, w, h);

      drawAurora(t, boost);
      drawStreams(t, mx, my, boost);
      drawNetwork(t, mx, my, boost);
      drawCursor(mx, my, boost);

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

      frameId = requestAnimationFrame(render);
    }

    let lastRipple = 0;
    const onMove = (e) => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (!rect) return;
      mouseRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        active: true,
      };
      const now = performance.now();
      if (now - lastRipple > 180) {
        ripples.push({
          x: mouseRef.current.x,
          y: mouseRef.current.y,
          r: 10,
          alpha: 0.28,
          speed: 2.8,
        });
        lastRipple = now;
      }
    };

    const onLeave = () => {
      mouseRef.current.active = false;
    };

    const onClick = (e) => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (!rect) return;
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      ripples.push({ x, y, r: 14, alpha: 0.42, speed: 3.5 });
      ripples.push({ x, y, r: 8, alpha: 0.28, speed: 2.2 });
    };

    resize();
    frameId = requestAnimationFrame(render);
    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mousedown", onClick);
    document.addEventListener("mouseleave", onLeave);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mousedown", onClick);
      document.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden />
  );
}
