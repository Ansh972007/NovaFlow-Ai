"use client";

const RING_COLORS = {
  trigger: { stroke: "#10b981", glow: "rgba(16,185,129,0.35)", dot: "#34d399" },
  retrieve: { stroke: "#0ea5e9", glow: "rgba(14,165,233,0.35)", dot: "#38bdf8" },
  llm: { stroke: "#8b5cf6", glow: "rgba(139,92,246,0.35)", dot: "#a78bfa" },
  output: { stroke: "#525252", glow: "rgba(82,82,82,0.28)", dot: "#737373" },
};

export default function WorkflowSelectionRing({ type = "output", size = 148 }) {
  const c = RING_COLORS[type] || RING_COLORS.output;
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;

  return (
    <div
      className="wf-selection-ring pointer-events-none absolute inset-0"
      style={{ width: size, height: size }}
      aria-hidden
    >
      <div className="wf-ring-ripple absolute inset-0 rounded-full" style={{ boxShadow: `0 0 40px ${c.glow}` }} />
      <div className="wf-ring-ripple wf-ring-ripple-2 absolute inset-0 rounded-full" />

      <svg width={size} height={size} className="absolute inset-0 overflow-visible">
        <defs>
          <linearGradient id={`wf-grad-${type}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={c.stroke} stopOpacity="0.15" />
            <stop offset="50%" stopColor={c.stroke} stopOpacity="1" />
            <stop offset="100%" stopColor={c.stroke} stopOpacity="0.15" />
          </linearGradient>
        </defs>

        <circle
          cx={cx}
          cy={cy}
          r={r + 6}
          fill="none"
          stroke={c.stroke}
          strokeWidth="1"
          strokeOpacity="0.12"
        />

        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={`url(#wf-grad-${type})`}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="24 14 8 14"
          className="wf-ring-orbit"
          style={{ transformOrigin: `${cx}px ${cy}px` }}
        />

        <circle
          cx={cx}
          cy={cy}
          r={r - 4}
          fill="none"
          stroke={c.stroke}
          strokeWidth="1.5"
          strokeOpacity="0.35"
          strokeDasharray="4 8"
          className="wf-ring-orbit-reverse"
          style={{ transformOrigin: `${cx}px ${cy}px` }}
        />
      </svg>

      {[0, 120, 240].map((deg) => (
        <div
          key={deg}
          className="wf-orbit-dot absolute left-1/2 top-1/2 h-full w-full"
          style={{ transform: `rotate(${deg}deg)`, animationDelay: `${deg / 360}s` }}
        >
          <span
            className="wf-orbit-dot-inner absolute left-1/2 block h-2 w-2 -translate-x-1/2 rounded-full"
            style={{
              top: `${cy - r - 2}px`,
              background: c.dot,
              boxShadow: `0 0 10px ${c.glow}`,
            }}
          />
        </div>
      ))}

      <div
        className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{ background: c.stroke, boxShadow: `0 0 12px ${c.glow}` }}
      >
        <span className="wf-core-ping absolute inset-0 rounded-full" style={{ background: c.stroke }} />
      </div>
    </div>
  );
}

export { RING_COLORS };
