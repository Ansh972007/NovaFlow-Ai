"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import AnimatedCounter from "@/components/AnimatedCounter";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import {
  DOC_CATEGORIES,
  NODE_TYPES,
  TEMPLATE_DOCS,
  getTemplatesByCategory,
} from "@/lib/docs/templateCatalog";

const ease = [0.16, 1, 0.3, 1];
const spring = { type: "spring", stiffness: 420, damping: 34 };

const CATEGORY_STATS = {
  workflows: 13,
  digests: 5,
  prompts: 5,
  nodes: 12,
};

const INNER_POOL = ["matrix", "constellation", "radar", "orbit", "cascade", "pulsefield", "stream", "hex"];
const CARD_BORDER_TYPES = ["needle", "arc", "tick", "beam", "filigree", "breathe", "stitch", "comet"];

function hashStr(s) {
  return [...s].reduce((a, c) => a + c.charCodeAt(0), 0);
}

function getCardBorder(id) {
  return CARD_BORDER_TYPES[hashStr(id) % CARD_BORDER_TYPES.length];
}

function getCardInner(index) {
  return INNER_POOL[index % INNER_POOL.length];
}

function GodBorder({ type, active, intense = false, tone = "dark" }) {
  if (!active) return null;
  const r = intense ? 20 : 16;
  const common = "pointer-events-none absolute inset-0 h-full w-full overflow-visible";
  const vb = "0 0 100 100";
  const stroke = tone === "light" ? "white" : "black";
  const dotBg = tone === "light" ? "bg-white" : "bg-black";
  const scanBg = tone === "light" ? "bg-white" : "bg-black";
  const thin = intense ? 1.1 : 1;
  const rx = r * 0.72;

  const frame = (extra) => (
    <svg className={common} preserveAspectRatio="none" viewBox={vb}>
      {extra}
    </svg>
  );

  if (type === "needle" || type === "march") {
    return frame(
      <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth={thin} strokeDasharray="4 10" animate={{ strokeDashoffset: [0, -28] }} transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }} />
    );
  }

  if (type === "arc" || type === "shimmer") {
    return frame(
      <>
        {[0, 1, 2, 3].map((c) => (
          <motion.path
            key={c}
            d={c === 0 ? "M12 2 H22" : c === 1 ? "M78 2 H88" : c === 2 ? "M2 78 V88" : "M98 78 V88"}
            fill="none" stroke={stroke} strokeWidth={thin} strokeLinecap="round"
            animate={{ opacity: [0.15, 0.9, 0.15], pathLength: [0.3, 1, 0.3] }}
            transition={{ duration: 1.6, repeat: Infinity, delay: c * 0.22, ease: "easeInOut" }}
          />
        ))}
      </>
    );
  }

  if (type === "tick" || type === "trace") {
    return frame(
      <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth={thin} pathLength="1" strokeDasharray="0.06 0.94" animate={{ strokeDashoffset: [0, -1] }} transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }} />
    );
  }

  if (type === "beam" || type === "scan") {
    return (
      <>
        {frame(
          <rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.2" />
        )}
        <motion.div className={`pointer-events-none absolute inset-x-6 top-0 h-px ${scanBg}`} animate={{ y: [0, 110, 0], opacity: [0, 0.7, 0] }} transition={{ duration: 2.8, repeat: Infinity, ease: "linear" }} />
      </>
    );
  }

  if (type === "filigree" || type === "wire") {
    return frame(
      <>
        <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth={thin} strokeDasharray="2 12" animate={{ strokeDashoffset: [0, -28] }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }} />
        <motion.rect x="5" y="5" width="90" height="90" rx={rx - 2} fill="none" stroke={stroke} strokeWidth="0.6" strokeOpacity="0.35" strokeDasharray="1 9" animate={{ strokeDashoffset: [0, 20] }} transition={{ duration: 2.8, repeat: Infinity, ease: "linear" }} />
      </>
    );
  }

  if (type === "breathe" || type === "gleam" || type === "pulse") {
    return frame(
      <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth={thin} animate={{ strokeOpacity: [0.2, 0.95, 0.2] }} transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }} />
    );
  }

  if (type === "stitch" || type === "halo") {
    return frame(
      <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth={thin} strokeDasharray="1 5 1 11" animate={{ strokeDashoffset: [0, -36] }} transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }} />
    );
  }

  if (type === "comet" || type === "filament") {
    return (
      <>
        {frame(
          <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.25" />
        )}
        <motion.div
          className={`pointer-events-none absolute h-1 w-1 rounded-full ${dotBg}`}
          animate={{ top: ["2%", "2%", "98%", "98%", "2%"], left: ["2%", "98%", "98%", "2%", "2%"], opacity: [0.2, 1, 1, 1, 0.2] }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "linear" }}
        />
      </>
    );
  }

  if (type === "prism" || type === "ripple") {
    return frame(
      <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth={thin} strokeDasharray="8 4 2 4" animate={{ strokeDashoffset: [0, -36] }} transition={{ duration: 2.4, repeat: Infinity, ease: "linear" }} />
    );
  }

  if (type === "orbitline" || type === "whisper") {
    return (
      <>
        {frame(
          <motion.rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth={thin} strokeDasharray="3 7" animate={{ strokeDashoffset: [0, 20] }} transition={{ duration: 3, repeat: Infinity, ease: "linear" }} />
        )}
        <motion.div className={`pointer-events-none absolute right-3 top-3 h-0.5 w-0.5 rounded-full ${dotBg}`} animate={{ scale: [0.5, 1.2, 0.5], opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity }} />
      </>
    );
  }

  return null;
}

function CardInnerStage({ type, active, nodes, reducedMotion, bare = false }) {
  const show = active && !reducedMotion;

  return (
    <div className={`relative mt-3 w-full overflow-hidden transition-colors duration-500 ${bare ? "h-28 rounded-2xl bg-gradient-to-br from-neutral-100/90 via-white to-neutral-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]" : `h-24 rounded-xl border ${active ? "border-black/25 bg-neutral-100" : "border-neutral-200/80 bg-neutral-50"}`}`}>
      {!show && (
        <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "repeating-linear-gradient(90deg,#00000008 0,#00000008 1px,transparent 1px,transparent 10px)" }} />
      )}

      {show && type === "matrix" && (
        <div className="grid h-full grid-cols-10 grid-rows-4 gap-px p-2">
          {Array.from({ length: 40 }).map((_, i) => (
            <motion.div
              key={i}
              className="rounded-sm bg-black"
              animate={{ opacity: [0.04, 0.7, 0.04], scale: [0.6, 1, 0.6] }}
              transition={{ duration: 1.4, repeat: Infinity, delay: (i % 10) * 0.05 + Math.floor(i / 10) * 0.12 }}
            />
          ))}
        </div>
      )}

      {show && type === "constellation" && (
        <svg className="absolute inset-0 h-full w-full">
          {[[15, 20], [45, 35], [75, 18], [60, 55], [25, 60]].map(([x, y], i) => (
            <motion.circle key={i} cx={`${x}%`} cy={`${y}%`} r="2.5" fill="black" animate={{ opacity: [0.2, 1, 0.2], r: [2, 3.5, 2] }} transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }} />
          ))}
          <motion.path d="M15 20 L45 35 L75 18 L60 55 L25 60 L15 20" fill="none" stroke="black" strokeWidth="0.8" strokeOpacity="0.3" pathLength="1" strokeDasharray="0.05 0.95" animate={{ strokeDashoffset: [0, -1] }} transition={{ duration: 3, repeat: Infinity, ease: "linear" }} />
          <motion.circle r="2" fill="black" animate={{ cx: ["10%", "90%", "10%"], cy: ["50%", "30%", "50%"], opacity: [0, 1, 0] }} transition={{ duration: 2.5, repeat: Infinity }} />
        </svg>
      )}

      {show && type === "radar" && (
        <div className="relative flex h-full items-center justify-center">
          {[0, 1, 2, 3].map((i) => (
            <motion.div key={i} className="absolute rounded-full border border-black" style={{ width: 20 + i * 22, height: 20 + i * 22 }} animate={{ scale: [0.4, 1.8], opacity: [0.7, 0] }} transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.45, ease: "easeOut" }} />
          ))}
          <motion.div className="absolute h-14 w-0.5 origin-bottom bg-gradient-to-t from-black to-transparent" animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }} />
          <div className="relative z-10 h-2.5 w-2.5 rounded-full bg-black" />
        </div>
      )}

      {show && type === "orbit" && (
        <div className="flex h-full items-center justify-center gap-1 px-2">
          {nodes.map((n, i) => (
            <div key={`${n}-${i}`} className="flex items-center">
              <motion.span
                className="rounded border border-black/25 bg-white px-1 py-0.5 text-[7px] font-bold uppercase"
                animate={{ opacity: [0.35, 1, 0.35], y: [0, -2, 0] }}
                transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.18 }}
              >
                {n.length > 8 ? n.slice(0, 7) + "…" : n}
              </motion.span>
              {i < nodes.length - 1 && (
                <motion.span className="mx-0.5 text-[7px] text-black/40" animate={{ opacity: [0.2, 0.8, 0.2] }} transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}>
                  →
                </motion.span>
              )}
            </div>
          ))}
        </div>
      )}

      {show && type === "cascade" && (
        <div className="flex h-full flex-col justify-center gap-1.5 px-3">
          {[0, 1, 2, 3].map((i) => (
            <motion.div
              key={i}
              className="h-1.5 rounded-full bg-black"
              animate={{ width: ["20%", "85%", "40%"], opacity: [0.2, 0.85, 0.2], x: [-20, 10, -20] }}
              transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.25, ease: "easeInOut" }}
            />
          ))}
        </div>
      )}

      {show && type === "pulsefield" && (
        <div className="flex h-full items-end gap-0.5 px-2 pb-2">
          {Array.from({ length: 16 }).map((_, i) => (
            <motion.div
              key={i}
              className="flex-1 rounded-t-sm bg-black"
              animate={{ height: ["15%", "95%", "25%"] }}
              transition={{ duration: 0.55 + (i % 4) * 0.1, repeat: Infinity, delay: i * 0.04, ease: "easeInOut" }}
            />
          ))}
        </div>
      )}

      {show && type === "stream" && (
        <>
          <motion.div className="absolute inset-0" style={{ background: "repeating-linear-gradient(90deg,transparent,transparent 8px,#00000012 8px,#00000012 9px)" }} animate={{ x: [0, 18] }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }} />
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute top-1/2 h-px w-8 -translate-y-1/2 bg-black"
              animate={{ left: ["-10%", "110%"], opacity: [0, 0.8, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, delay: i * 0.5, ease: "linear" }}
            />
          ))}
        </>
      )}

      {show && type === "hex" && (
        <svg className="absolute inset-0 h-full w-full p-2" viewBox="0 0 120 48">
          {[[20, 24], [60, 12], [100, 24], [60, 36]].map(([x, y], i) => (
            <motion.polygon
              key={i}
              points={`${x},${y - 8} ${x + 7},${y - 4} ${x + 7},${y + 4} ${x},${y + 8} ${x - 7},${y + 4} ${x - 7},${y - 4}`}
              fill="none" stroke="black" strokeWidth="1"
              animate={{ opacity: [0.15, 0.9, 0.15], scale: [0.85, 1.05, 0.85] }}
              transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.2 }}
              style={{ transformOrigin: `${x}px ${y}px` }}
            />
          ))}
        </svg>
      )}

      {show && (
        <motion.div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-black/40" animate={{ scaleX: [0.2, 1, 0.2], opacity: [0.2, 0.7, 0.2] }} transition={{ duration: 2, repeat: Infinity }} />
      )}
    </div>
  );
}

function LiveNodeRiver({ nodes, active, bare = false }) {
  return (
    <div className={`mt-3 flex items-center gap-1 overflow-hidden rounded-xl px-2 py-2 ${bare ? "bg-neutral-100/70" : "rounded-lg border border-neutral-200 bg-white"}`}>
      {nodes.slice(0, 6).map((n, i) => (
        <div key={`${n}-${i}`} className="flex items-center">
          <motion.span
            className={`relative rounded-md px-2 py-1 text-[8px] font-bold uppercase ${active ? "bg-black text-white" : "bg-neutral-100 text-neutral-600"}`}
            animate={active ? { boxShadow: ["0 0 0 0 rgba(0,0,0,0)", "0 0 0 6px rgba(0,0,0,0.08)", "0 0 0 0 rgba(0,0,0,0)"] } : {}}
            transition={{ delay: i * 0.2, duration: 1.2, repeat: active ? Infinity : 0 }}
          >
            {n.slice(0, 5)}
            {active && (
              <motion.span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-white ring-1 ring-black" animate={{ scale: [0, 1, 0] }} transition={{ delay: i * 0.2 + 0.3, duration: 0.8, repeat: Infinity }} />
            )}
          </motion.span>
          {i < Math.min(nodes.length, 6) - 1 && (
            <motion.span className="mx-0.5 text-[9px] text-neutral-400" animate={active ? { opacity: [0.2, 1, 0.2], x: [0, 2, 0] } : {}} transition={{ delay: i * 0.15, duration: 0.9, repeat: active ? Infinity : 0 }}>
              ▸
            </motion.span>
          )}
        </div>
      ))}
    </div>
  );
}

function CinematicFlowDiagram({ nodes, active, templateId }) {
  const reducedMotion = useReducedMotion();
  const count = nodes.length;
  const spacing = count <= 3 ? 120 : count <= 4 ? 105 : 90;
  const width = Math.max(280, (count - 1) * spacing + 100);
  const startX = 50;
  const positions = nodes.map((_, i) => ({ x: startX + i * spacing, y: 72 }));
  const gradId = `flow-grad-${templateId || nodes.join("-")}`;

  function nodeLabel(node) {
    if (node.length <= 10) return node;
    return node.split(/[\s/]+/).map((w) => w.slice(0, 4)).join("·");
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-black/[0.08] bg-neutral-950 p-4 sm:p-6">
      {!reducedMotion && active && (
        <>
          <motion.div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(255,255,255,0.08),transparent_45%)]"
            animate={{ opacity: [0.3, 0.7, 0.3], scale: [1, 1.05, 1] }}
            transition={{ duration: 4, repeat: Infinity }}
          />
          <motion.div
            className="pointer-events-none absolute inset-0 opacity-30"
            style={{ backgroundImage: "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,0.03) 2px,rgba(255,255,255,0.03) 4px)" }}
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          />
        </>
      )}

      <div className="relative mb-3 flex items-center gap-2">
        <div className="flex gap-1.5">
          {["#ef4444", "#eab308", "#22c55e"].map((c, i) => (
            <motion.span
              key={c}
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: c }}
              animate={active && !reducedMotion ? { scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] } : {}}
              transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
        <span className="text-[11px] font-medium text-neutral-500">Pipeline simulator</span>
        {active && !reducedMotion && (
          <motion.span className="ml-auto text-[9px] font-bold tracking-widest text-white/40 uppercase" animate={{ opacity: [0.2, 0.8, 0.2] }} transition={{ duration: 1.2, repeat: Infinity }}>
            live
          </motion.span>
        )}
      </div>

      <svg viewBox={`0 0 ${width} 130`} className="relative w-full" style={{ minHeight: 130 }}>
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="white" stopOpacity="0.1" />
            <stop offset="50%" stopColor="white" stopOpacity="0.95" />
            <stop offset="100%" stopColor="white" stopOpacity="0.1" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {positions.slice(0, -1).map((p, i) => {
          const next = positions[i + 1];
          const midX = (p.x + next.x) / 2;
          const midY = p.y - 12;
          const pathD = `M${p.x} ${p.y} Q${midX} ${midY} ${next.x} ${next.y}`;
          return (
            <g key={`edge-${i}`}>
              <path d={pathD} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2" />
              {active && !reducedMotion && (
                <>
                  <motion.path
                    d={pathD}
                    fill="none"
                    stroke={`url(#${gradId})`} strokeWidth="2"
                    strokeDasharray="10 14"
                    animate={{ strokeDashoffset: [0, -48] }}
                    transition={{ duration: 0.9, repeat: Infinity, ease: "linear", delay: i * 0.12 }}
                  />
                  <motion.circle
                    r="5" fill="white" filter="url(#glow)"
                    animate={{
                      cx: [p.x, midX, next.x, midX, p.x],
                      cy: [p.y, midY, next.y, midY, p.y],
                      opacity: [0, 1, 1, 1, 0],
                    }}
                    transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.35, ease: "easeInOut" }}
                  />
                </>
              )}
            </g>
          );
        })}

        {positions.map((p, i) => (
          <g key={`${templateId || "map"}-${nodes[i]}-${i}`}>
            {active && !reducedMotion && (
              <motion.circle
                cx={p.x} cy={p.y} r="26"
                fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1"
                animate={{ r: [20, 30, 20], opacity: [0.4, 0, 0.4] }}
                transition={{ delay: i * 0.25, duration: 2, repeat: Infinity }}
              />
            )}
            <motion.circle
              cx={p.x} cy={p.y} r="20"
              fill={active && !reducedMotion ? "white" : "rgba(255,255,255,0.08)"}
              stroke="rgba(255,255,255,0.35)" strokeWidth="1.2"
              animate={
                active && !reducedMotion
                  ? { scale: [1, 1.1, 1], fill: ["#ffffff", "#d4d4d4", "#ffffff"] }
                  : {}
              }
              transition={{ delay: i * 0.3, duration: 1.1, repeat: active ? Infinity : 0, repeatDelay: count * 0.28 }}
            />
            <text x={p.x} y={p.y + 3} textAnchor="middle" className="fill-neutral-950 font-bold uppercase" style={{ fontSize: 8 }}>
              {nodeLabel(nodes[i])}
            </text>
            <text x={p.x} y={p.y + 42} textAnchor="middle" fill="rgba(255,255,255,0.55)" style={{ fontSize: 7 }}>
              {nodes[i]}
            </text>
          </g>
        ))}
      </svg>

      {!reducedMotion && active && (
        <>
          <motion.div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-white/50 to-transparent"
            animate={{ x: ["-100%", "100%"] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-white/[0.04] to-transparent"
            animate={{ opacity: [0.2, 0.6, 0.2] }}
            transition={{ duration: 3, repeat: Infinity }}
          />
        </>
      )}
    </div>
  );
}

function MiniFlowStrip({ nodes, active }) {
  return <LiveNodeRiver nodes={nodes} active={active} />;
}

function TemplateDocCard({ tpl, active, onSelect, index }) {
  const reducedMotion = useReducedMotion();
  const borderAnim = getCardBorder(tpl.id);
  const innerAnim = getCardInner(index);

  return (
    <motion.button
      type="button"
      layout
      initial={{ opacity: 0, y: 28, rotateX: 8 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ delay: index * 0.05, duration: 0.5, ease }}
      whileHover={reducedMotion ? {} : { y: -10, scale: 1.02, rotateX: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(tpl)}
      className={`noise group relative flex min-h-[14rem] w-full flex-col overflow-hidden rounded-[1.25rem] border text-left ${
        active
          ? "border-transparent bg-neutral-50 shadow-[0_24px_70px_-24px_rgba(0,0,0,0.55)]"
          : "border-neutral-200 bg-white hover:border-neutral-400 hover:shadow-xl hover:shadow-black/10"
      }`}
      style={{ perspective: 900 }}
    >
      {!reducedMotion && <GodBorder type={borderAnim} active={active} />}

      {active && !reducedMotion && (
        <motion.div
          className="pointer-events-none absolute -inset-px rounded-[1.25rem] bg-[radial-gradient(circle_at_50%_0%,rgba(0,0,0,0.06),transparent_55%)]"
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 2.5, repeat: Infinity }}
        />
      )}

      <div className="relative flex flex-1 flex-col p-5">
        <div className="flex items-start justify-between gap-2">
          <motion.span
            className="flex h-7 w-7 items-center justify-center rounded-lg bg-black text-[10px] font-bold text-white"
            animate={active ? { scale: [1, 1.08, 1] } : {}}
            transition={{ duration: 1.2, repeat: active ? Infinity : 0 }}
          >
            {String(index + 1).padStart(2, "0")}
          </motion.span>
          {active && !reducedMotion && (
            <motion.span
              className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-black bg-white text-[10px] font-bold"
              initial={{ scale: 0, rotate: -90 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={spring}
            >
              ✓
            </motion.span>
          )}
        </div>

        <h3 className="mt-4 font-serif text-xl tracking-tight text-neutral-900">{tpl.name}</h3>
        <p className="mt-1.5 text-xs leading-relaxed text-neutral-500">{tpl.desc}</p>

        <CardInnerStage type={innerAnim} active={active} nodes={tpl.nodes} reducedMotion={reducedMotion} />

        <LiveNodeRiver nodes={tpl.nodes} active={active} />

        <p className={`mt-3 text-[10px] font-bold tracking-[0.14em] uppercase ${active ? "text-black" : "text-neutral-400 opacity-0 group-hover:opacity-100"}`}>
          {active ? "▼ Guide open below" : "Open full guide →"}
        </p>
      </div>

      {active && !reducedMotion && (
        <>
          <motion.div className="absolute bottom-0 left-0 h-1 bg-black" initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 0.7, ease }} />
          <motion.div className="pointer-events-none absolute top-0 right-0 h-16 w-16 bg-gradient-to-bl from-black/[0.04] to-transparent" animate={{ opacity: [0.3, 0.7, 0.3] }} transition={{ duration: 2, repeat: Infinity }} />
        </>
      )}
    </motion.button>
  );
}

function resolveNodeMeta(nodeName) {
  const lower = nodeName.toLowerCase();
  return (
    NODE_TYPES.find(
      (n) => lower === n.id || lower.includes(n.id) || n.label.toLowerCase() === lower
    ) || null
  );
}

function getTemplateVariables(nodes) {
  const joined = nodes.join(" ").toLowerCase();
  const vars = [];
  if (/trigger|transform|llm|agent|loop/.test(joined)) vars.push({ key: "{{input}}", desc: "Raw user or webhook payload" });
  if (/llm|transform|notify|output|jira|github|linear|agent/.test(joined)) vars.push({ key: "{{output}}", desc: "Text from the prior node" });
  if (/notify|digest|email/.test(joined)) vars.push({ key: "{{subject}}", desc: "Parsed subject line for delivery" });
  if (/loop/.test(joined)) vars.push({ key: "{{item}}", desc: "Single line inside a batch loop" });
  return vars;
}

const CATEGORY_LABELS = {
  workflows: "Workflow pipeline",
  digests: "Scheduled digest",
  prompts: "App & prompt preset",
};

function DeepDiveStat({ label, value, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.45, ease }}
      className="rounded-2xl bg-white/90 px-4 py-3 shadow-[0_8px_30px_-12px_rgba(0,0,0,0.12)] backdrop-blur-sm"
    >
      <p className="text-[10px] font-bold tracking-[0.14em] text-neutral-400 uppercase">{label}</p>
      <p className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">{value}</p>
    </motion.div>
  );
}

function ConfigTimeline({ steps, soft = false }) {
  const reducedMotion = useReducedMotion();
  const cardCls = soft
    ? "noise min-w-0 flex-1 overflow-hidden rounded-2xl bg-white p-5 shadow-[0_12px_40px_-18px_rgba(0,0,0,0.14)]"
    : "noise min-w-0 flex-1 overflow-hidden rounded-2xl border border-black/[0.07] bg-gradient-to-br from-white via-white to-neutral-50 p-5 shadow-sm";

  return (
    <ol className="relative space-y-0">
      <motion.span
        className="absolute top-5 bottom-5 left-[1.125rem] w-px bg-gradient-to-b from-black/20 via-black/10 to-transparent"
        initial={{ scaleY: 0 }}
        whileInView={{ scaleY: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, ease }}
        style={{ transformOrigin: "top" }}
      />
      {!reducedMotion && (
        <motion.span
          className="absolute left-[1.02rem] h-2 w-2 rounded-full bg-black"
          animate={{ y: [0, steps.length * 88, 0], opacity: [0, 1, 1, 0] }}
          transition={{ duration: steps.length * 1.2, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
      {steps.map((step, i) => (
        <motion.li
          key={step.title}
          initial={{ opacity: 0, x: -24 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: "-24px" }}
          transition={{ delay: i * 0.07, duration: 0.5, ease }}
          className="relative flex gap-5 pb-7 last:pb-0"
        >
          <motion.span
            className="relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-black bg-black text-xs font-bold text-white shadow-lg shadow-black/15"
            whileInView={{ scale: [0.7, 1.08, 1] }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.07, duration: 0.45 }}
          >
            {String(i + 1).padStart(2, "0")}
          </motion.span>
          <motion.div
            whileHover={reducedMotion ? {} : { y: -3, boxShadow: "0 16px 40px -20px rgba(0,0,0,0.25)" }}
            className={cardCls}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <p className="font-semibold text-neutral-900">{step.title}</p>
              <span className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-[10px] font-bold tracking-wide text-neutral-500 uppercase">
                Step {i + 1}
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">{step.detail}</p>
            {step.href && (
              <Link
                href={step.href}
                className="mt-4 inline-flex items-center gap-2 rounded-full border border-black bg-black px-4 py-2 text-xs font-bold text-white transition hover:bg-neutral-800"
              >
                Open {step.href}
                <motion.span animate={{ x: [0, 4, 0] }} transition={{ duration: 1.2, repeat: Infinity }}>→</motion.span>
              </Link>
            )}
          </motion.div>
        </motion.li>
      ))}
    </ol>
  );
}

function NodePlaybook({ nodes, soft = false }) {
  const reducedMotion = useReducedMotion();
  const cardCls = soft
    ? "group relative overflow-hidden rounded-2xl bg-white p-4 shadow-[0_10px_36px_-16px_rgba(0,0,0,0.12)] transition hover:shadow-[0_18px_48px_-20px_rgba(0,0,0,0.18)]"
    : "group relative overflow-hidden rounded-2xl border border-neutral-200 bg-white p-4 transition hover:border-black hover:shadow-lg hover:shadow-black/5";

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {nodes.map((nodeName, i) => {
        const meta = resolveNodeMeta(nodeName);
        return (
          <motion.div
            key={`${nodeName}-${i}`}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05, ease }}
            whileHover={reducedMotion ? {} : { y: -4 }}
            className={cardCls}
          >
            <motion.div
              className="pointer-events-none absolute inset-0 bg-gradient-to-br from-neutral-100/80 to-transparent opacity-0 transition group-hover:opacity-100"
              transition={{ duration: 0.3 }}
            />
            <div className="relative flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-black font-mono text-[10px] font-bold text-white uppercase">
                {meta?.id?.slice(0, 2) || String(i + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-neutral-900">{meta?.label || nodeName}</p>
                <p className="mt-1 text-xs leading-relaxed text-neutral-500">
                  {meta?.role || "Custom pipeline step in this template."}
                </p>
              </div>
            </div>
            {meta && (
              <div className={`relative mt-4 space-y-2 pt-3 text-[11px] ${soft ? "" : "border-t border-neutral-100"}`}>
                <p className="font-bold tracking-wide text-neutral-400 uppercase">Emits</p>
                <div className="flex flex-wrap gap-1.5">
                  {meta.outputs.map((o) => (
                    <span key={o} className="rounded-md bg-neutral-100 px-2 py-0.5 text-neutral-700">
                      {o}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

function IntegrationGrid({ items, soft = false }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((item, i) => (
        <motion.div
          key={item}
          initial={{ opacity: 0, scale: 0.94 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.06, type: "spring", stiffness: 380, damping: 28 }}
          className={soft
            ? "flex items-center gap-3 rounded-2xl bg-gradient-to-r from-neutral-100/80 to-white px-4 py-3.5 shadow-[0_8px_28px_-14px_rgba(0,0,0,0.1)]"
            : "flex items-center gap-3 rounded-2xl border border-neutral-200 bg-gradient-to-r from-neutral-50 to-white px-4 py-3.5"}
        >
          <span className="relative flex h-2.5 w-2.5 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-neutral-400 opacity-40" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-black" />
          </span>
          <p className="text-sm font-semibold text-neutral-800">{item}</p>
        </motion.div>
      ))}
    </div>
  );
}

function TipsGallery({ tips, soft = false }) {
  return (
    <div className="grid gap-3">
      {tips.map((tip, i) => (
        <motion.div
          key={tip}
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.06, ease }}
          className={soft
            ? "group relative overflow-hidden rounded-2xl bg-white p-4 shadow-[0_10px_32px_-16px_rgba(0,0,0,0.1)] sm:p-5"
            : "group relative overflow-hidden rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5"}
        >
          <motion.div
            className="pointer-events-none absolute -right-4 -top-4 h-16 w-16 rounded-full bg-neutral-100 opacity-0 transition group-hover:opacity-100"
            animate={{ scale: [1, 1.15, 1] }}
            transition={{ duration: 3, repeat: Infinity }}
          />
          <div className="relative flex gap-4">
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg font-serif text-sm text-neutral-900 ${soft ? "bg-neutral-100" : "border border-black/10 bg-neutral-50"}`}>
              {i + 1}
            </span>
            <p className="text-sm leading-relaxed text-neutral-700">{tip}</p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function VariableStrip({ variables, soft = false }) {
  if (!variables.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {variables.map((v, i) => (
        <motion.div
          key={v.key}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 + i * 0.05 }}
          className={soft
            ? "rounded-xl bg-neutral-100/80 px-3 py-2 shadow-[0_6px_20px_-12px_rgba(0,0,0,0.12)]"
            : "rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2"}
        >
          <code className="text-xs font-bold text-neutral-900">{v.key}</code>
          <p className="mt-0.5 text-[11px] text-neutral-500">{v.desc}</p>
        </motion.div>
      ))}
    </div>
  );
}

function TemplateDetailPanel({ tpl, innerAnim }) {
  const reducedMotion = useReducedMotion();
  const variables = getTemplateVariables(tpl.nodes);
  const stepCount = tpl.configure?.length || 0;
  const integrationCount = tpl.integrations?.length || 0;

  return (
    <motion.div
      key={tpl.id}
      initial={{ opacity: 0, y: 40, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 24, scale: 0.99 }}
      transition={{ duration: 0.65, ease }}
      className="relative"
    >
      <motion.div
        className="absolute -inset-8 rounded-[3rem] bg-[radial-gradient(ellipse_at_50%_0%,rgba(0,0,0,0.06),transparent_65%)]"
        animate={{ opacity: [0.5, 0.9, 0.5] }}
        transition={{ duration: 5, repeat: Infinity }}
      />

      <div className="noise relative overflow-hidden rounded-[2rem] bg-white shadow-[0_32px_80px_-32px_rgba(0,0,0,0.22)]">
        {!reducedMotion && (
          <motion.div
            className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-neutral-100/50 to-transparent"
            animate={{ opacity: [0.4, 0.8, 0.4] }}
            transition={{ duration: 4, repeat: Infinity }}
          />
        )}

        <div className="relative px-6 py-8 sm:px-10 sm:py-10">
          <div className="flex flex-wrap items-center gap-2">
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="rounded-full bg-neutral-100 px-3 py-1 text-[10px] font-bold tracking-[0.14em] text-neutral-600 uppercase"
            >
              {CATEGORY_LABELS[tpl.category] || tpl.category}
            </motion.span>
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.05 }}
              className="rounded-full bg-black px-3 py-1 text-[10px] font-bold tracking-wide text-white uppercase"
            >
              {tpl.id}
            </motion.span>
          </div>

          <div className="mt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(260px,340px)] lg:items-start lg:gap-10">
            <div>
              <motion.p
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-[11px] font-semibold tracking-[0.2em] text-neutral-400 uppercase"
              >
                Deep dive
              </motion.p>
              <motion.h2
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="mt-2 font-serif text-3xl tracking-tight text-neutral-900 sm:text-4xl lg:text-[2.75rem] lg:leading-[1.05]"
              >
                {tpl.name}
              </motion.h2>
              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="mt-3 text-sm font-medium text-neutral-500"
              >
                {tpl.desc}
              </motion.p>
              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.14 }}
                className="mt-3 max-w-2xl text-base leading-relaxed text-neutral-600"
              >
                {tpl.tagline}
              </motion.p>

              <div className="mt-6 grid grid-cols-3 gap-3 sm:max-w-md">
                <DeepDiveStat label="Nodes" value={tpl.nodes.length} delay={0.16} />
                <DeepDiveStat label="Steps" value={stepCount} delay={0.2} />
                <DeepDiveStat label="Connections" value={integrationCount} delay={0.24} />
              </div>
            </div>

            {!reducedMotion && (
              <motion.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.12, duration: 0.5, ease }}
                className="mt-6 lg:mt-0"
              >
                <CardInnerStage type={innerAnim} active nodes={tpl.nodes} reducedMotion={false} bare />
              </motion.div>
            )}
          </div>

          <div className="mt-8">
            <p className="workspace-section-label mb-3">Pipeline at a glance</p>
            <LiveNodeRiver nodes={tpl.nodes} active bare />
          </div>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-neutral-200 to-transparent" />

        <div className="grid gap-10 p-6 lg:grid-cols-[minmax(0,1fr)_minmax(300px,400px)] lg:gap-12 lg:p-10">
          <div className="space-y-12">
            <section>
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="workspace-section-label">How to configure</p>
                  <h3 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">
                    {stepCount}-step setup path
                  </h3>
                </div>
                <span className="text-xs text-neutral-400">Follow in order · links open the right screen</span>
              </div>
              <div className="mt-6">
                <ConfigTimeline steps={tpl.configure} soft />
              </div>
            </section>

            <section>
              <p className="workspace-section-label">Node playbook</p>
              <h3 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">What each piece does</h3>
              <p className="mt-2 text-sm text-neutral-500">
                Every node in this template — role, outputs, and how data flows through.
              </p>
              <div className="mt-5">
                <NodePlaybook nodes={tpl.nodes} soft />
              </div>
            </section>

            {tpl.integrations?.length > 0 && (
              <section>
                <p className="workspace-section-label">Required connections</p>
                <h3 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">Wire these first</h3>
                <div className="mt-5">
                  <IntegrationGrid items={tpl.integrations} soft />
                </div>
              </section>
            )}

            {variables.length > 0 && (
              <section>
                <p className="workspace-section-label">Template variables</p>
                <h3 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">Mustache placeholders</h3>
                <p className="mt-2 text-sm text-neutral-500">
                  Use these in transform, notify, and integration nodes for this pipeline.
                </p>
                <div className="mt-4">
                  <VariableStrip variables={variables} soft />
                </div>
              </section>
            )}

            {tpl.tips?.length > 0 && (
              <section>
                <p className="workspace-section-label">Pro tips</p>
                <h3 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">Ship faster</h3>
                <div className="mt-5">
                  <TipsGallery tips={tpl.tips} soft />
                </div>
              </section>
            )}

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="rounded-2xl bg-neutral-50 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]"
            >
              <p className="w-full text-[10px] font-bold tracking-[0.14em] text-neutral-400 uppercase">Quick launch</p>
              <div className="mt-3 flex flex-wrap gap-3">
                {(tpl.links || []).map((l, i) => (
                  <Link
                    key={l.href}
                    href={l.href}
                    className={i === 0 ? "btn-primary text-sm" : "inline-flex items-center rounded-full bg-white px-4 py-2 text-sm font-semibold text-neutral-800 shadow-[0_8px_24px_-14px_rgba(0,0,0,0.15)] transition hover:bg-neutral-100"}
                  >
                    {l.label}
                    {i > 0 && <span className="ml-1.5 text-neutral-400">→</span>}
                  </Link>
                ))}
              </div>
            </motion.div>
          </div>

          <div className="space-y-5 lg:sticky lg:top-24 lg:self-start">
            <div className="overflow-hidden rounded-[1.5rem] bg-neutral-950 p-4 shadow-[0_20px_50px_-24px_rgba(0,0,0,0.5)]">
              <p className="workspace-section-label mb-1 text-neutral-500">Live connection map</p>
              <p className="mb-4 text-xs text-neutral-500">
                {tpl.nodes.length} nodes · data flows left to right in run order
              </p>
              <CinematicFlowDiagram key={tpl.id} nodes={tpl.nodes} active templateId={tpl.id} />
            </div>

            <div className="rounded-[1.5rem] bg-neutral-50 p-4">
              <p className="text-[10px] font-bold tracking-[0.14em] text-neutral-400 uppercase">Run order</p>
              <ol className="mt-3 space-y-2">
                {tpl.nodes.map((n, i) => {
                  const meta = resolveNodeMeta(n);
                  return (
                    <motion.li
                      key={`${n}-${i}`}
                      initial={{ opacity: 0, x: 8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.2 + i * 0.06 }}
                      className="flex items-center gap-3 rounded-xl bg-white px-3 py-2.5 shadow-[0_6px_20px_-14px_rgba(0,0,0,0.08)]"
                    >
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-black text-[10px] font-bold text-white">
                        {i + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-xs font-semibold text-neutral-900">{meta?.label || n}</p>
                        <p className="truncate text-[10px] text-neutral-500">{n}</p>
                      </div>
                      {i < tpl.nodes.length - 1 && !reducedMotion && (
                        <motion.span
                          className="ml-auto text-[10px] text-neutral-300"
                          animate={{ opacity: [0.2, 0.8, 0.2] }}
                          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.15 }}
                        >
                          →
                        </motion.span>
                      )}
                    </motion.li>
                  );
                })}
              </ol>
            </div>

            {variables.length > 0 && (
              <div className="rounded-[1.5rem] bg-neutral-50 p-4">
                <p className="text-[10px] font-bold tracking-[0.14em] text-neutral-400 uppercase">Data contract</p>
                <p className="mt-2 text-xs leading-relaxed text-neutral-500">
                  Variables available in this template&apos;s nodes.
                </p>
                <div className="mt-3 space-y-2">
                  {variables.map((v) => (
                    <div key={v.key} className="rounded-xl bg-white px-3 py-2 shadow-[0_4px_16px_-12px_rgba(0,0,0,0.1)]">
                      <code className="text-[11px] font-bold text-neutral-900">{v.key}</code>
                      <p className="text-[10px] text-neutral-500">{v.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function NodeReferencePanel() {
  const reducedMotion = useReducedMotion();

  return (
    <div className="space-y-8">
      <CinematicFlowDiagram
        key="node-reference"
        nodes={["trigger", "retrieve", "llm", "notify", "output"]}
        active={!reducedMotion}
        templateId="node-reference"
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {NODE_TYPES.map((node, i) => (
          <motion.div
            key={node.id}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.04, ease }}
            whileHover={{ y: -6, transition: { duration: 0.2 } }}
            className="noise group relative overflow-hidden rounded-2xl border border-neutral-200 bg-white p-5 hover:border-black hover:shadow-lg"
          >
            <motion.div
              className="pointer-events-none absolute inset-0 bg-black/[0.02] opacity-0 group-hover:opacity-100"
              transition={{ duration: 0.3 }}
            />
            <div className="flex items-center gap-3">
              <motion.span
                className="flex h-11 w-11 items-center justify-center rounded-xl bg-black font-mono text-xs font-bold text-white uppercase"
                whileHover={{ rotate: [0, -4, 4, 0] }}
                transition={{ duration: 0.4 }}
              >
                {node.id.slice(0, 2)}
              </motion.span>
              <h3 className="font-serif text-lg text-neutral-900">{node.label}</h3>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">{node.role}</p>
            <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div>
                <p className="font-bold tracking-wide text-neutral-400 uppercase">Outputs</p>
                <ul className="mt-1 space-y-0.5 text-neutral-600">
                  {node.outputs.map((o) => <li key={o}>• {o}</li>)}
                </ul>
              </div>
              <div>
                <p className="font-bold tracking-wide text-neutral-400 uppercase">Config</p>
                <ul className="mt-1 space-y-0.5 text-neutral-600">
                  {node.config.slice(0, 3).map((c) => <li key={c}>• {c}</li>)}
                </ul>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function CategoryBentoTabs({ active, onChange }) {
  const reducedMotion = useReducedMotion();

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {DOC_CATEGORIES.map((cat, i) => {
        const isActive = active === cat.id;
        return (
          <motion.button
            key={cat.id}
            type="button"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 + i * 0.06, ease }}
            whileHover={{ y: -6, scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onChange(cat.id)}
            className={`relative overflow-hidden rounded-[1.25rem] border p-5 text-left transition ${
              isActive
                ? "border-transparent bg-black text-white shadow-2xl shadow-black/30"
                : "border-neutral-200 bg-white hover:border-neutral-400"
            }`}
          >
            {!reducedMotion && isActive && <GodBorder type={cat.borderAnim} active intense tone="light" />}

            {isActive && (
              <>
                <motion.div
                  className="pointer-events-none absolute -right-6 -top-6 h-28 w-28 rounded-full bg-white/10 blur-2xl"
                  animate={{ scale: [1, 1.3, 1], opacity: [0.4, 0.9, 0.4] }}
                  transition={{ duration: 2.5, repeat: Infinity }}
                />
                <motion.div
                  className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_0%,rgba(255,255,255,0.12),transparent_50%)]"
                  animate={{ opacity: [0.3, 0.7, 0.3] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </>
            )}

            <p className={`relative text-[10px] font-bold tracking-[0.16em] uppercase ${isActive ? "text-white/60" : "text-neutral-400"}`}>
              {CATEGORY_STATS[cat.id]} items
            </p>
            <p className="relative mt-2 font-serif text-xl tracking-tight">{cat.label}</p>
            <p className={`relative mt-1 text-xs ${isActive ? "text-white/70" : "text-neutral-500"}`}>{cat.desc}</p>
          </motion.button>
        );
      })}
    </div>
  );
}

const QUICK_START = [
  { n: "01", text: "Start API", code: ".\\deploy\\start-backend.ps1" },
  { n: "02", text: "Configure env", code: "cp .env.example .env.local" },
  { n: "03", text: "Run frontend", code: "npm run dev" },
  { n: "04", text: "Login", link: "/login", label: "admin / admin123 (local)" },
  { n: "05", text: "Verify", code: "npm run verify" },
];

export default function DocsClient() {
  const [category, setCategory] = useState("workflows");
  const [selectedId, setSelectedId] = useState("rag");

  const templates = useMemo(() => getTemplatesByCategory(category), [category]);
  const activeCategory = DOC_CATEGORIES.find((c) => c.id === category);
  const selected = useMemo(
    () => TEMPLATE_DOCS.find((t) => t.id === selectedId) || templates[0] || null,
    [selectedId, templates]
  );

  function pickCategory(id) {
    setCategory(id);
    if (id !== "nodes") {
      const first = getTemplatesByCategory(id)[0];
      if (first) setSelectedId(first.id);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground active />

      <div className="relative z-10">
        <AppHeader links={[{ href: "/", label: "Home" }, { href: "/login", label: "Sign in" }, { href: "/developer", label: "API" }]} />

        <main className="workspace-page-main mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14">
          <WorkspaceHero
            eyebrow="God's valley"
            title="Template"
            titleHighlight="universe"
            description="Every workflow, digest, and prompt — how to wire it, what each node does, and where every setting lives."
            badge={
              <span className="workspace-badge-live inline-flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-neutral-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-neutral-900" />
                </span>
                {TEMPLATE_DOCS.length} living guides
              </span>
            }
          />

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, ease }}
            className="mt-10 grid gap-4 sm:grid-cols-4"
          >
            {DOC_CATEGORIES.map((cat) => (
              <WorkspaceStatCard
                key={cat.id}
                label={cat.label}
                value={<AnimatedCounter value={String(CATEGORY_STATS[cat.id])} />}
                hint={cat.desc}
              />
            ))}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18, ease }}
            className="mt-12"
          >
            <p className="workspace-section-label">Explore</p>
            <h2 className="mt-1 font-serif text-2xl tracking-tight sm:text-3xl">Pick a universe</h2>
            <div className="mt-5">
              <CategoryBentoTabs active={category} onChange={pickCategory} />
            </div>
          </motion.div>

          <AnimatePresence mode="wait">
            {category === "nodes" ? (
              <motion.div key="nodes" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} transition={{ duration: 0.45 }} className="mt-12">
                <NodeReferencePanel />
              </motion.div>
            ) : (
              <motion.div key={category} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.5 }} className="mt-12">
                <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <h2 className="font-serif text-3xl tracking-tight">{activeCategory?.label}</h2>
                    <p className="mt-2 text-sm text-neutral-500">Select a card — cinematic guide unfolds below.</p>
                  </div>
                </div>

                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {templates.map((tpl, i) => (
                    <TemplateDocCard
                      key={tpl.id}
                      tpl={tpl}
                      index={i}
                      active={selectedId === tpl.id}
                      onSelect={(t) => {
                        setSelectedId(t.id);
                        setTimeout(() => {
                          document.getElementById("template-detail")?.scrollIntoView({ behavior: "smooth", block: "start" });
                        }, 100);
                      }}
                    />
                  ))}
                </div>

                {selected && (() => {
                  const selectedIndex = templates.findIndex((t) => t.id === selected.id);
                  return (
                  <div id="template-detail" className="mt-14">
                    <AnimatePresence mode="wait">
                      <TemplateDetailPanel
                        tpl={selected}
                        innerAnim={getCardInner(selectedIndex)}
                      />
                    </AnimatePresence>
                  </div>
                  );
                })()}
              </motion.div>
            )}
          </AnimatePresence>

          <motion.section
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-20"
          >
            <p className="workspace-section-label">Quick start</p>
            <h2 className="mt-1 font-serif text-2xl tracking-tight">Run locally</h2>
            <div className="workspace-panel noise mt-6 overflow-hidden rounded-[1.75rem] p-6 sm:p-8">
              <ol className="space-y-4">
                {QUICK_START.map((step, i) => (
                  <motion.li
                    key={step.n}
                    initial={{ opacity: 0, x: -12 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.06 }}
                    className="flex gap-4 text-sm"
                  >
                    <motion.span
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-black text-[10px] font-mono text-white"
                      whileInView={{ scale: [0, 1.2, 1] }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.06 }}
                    >
                      {step.n}
                    </motion.span>
                    <div className="pt-1 text-neutral-600">
                      {step.code ? (
                        <>
                          {step.text} <code className="workspace-code-block">{step.code}</code>
                        </>
                      ) : (
                        <>
                          {step.text}{" "}
                          <Link href={step.link} className="font-semibold text-neutral-900 underline-offset-2 hover:underline">
                            {step.label}
                          </Link>
                        </>
                      )}
                    </div>
                  </motion.li>
                ))}
              </ol>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/login?mode=register" className="btn-primary">Create account</Link>
                <Link href="/developer" className="workspace-btn-ghost">API playground →</Link>
              </div>
            </div>
          </motion.section>
        </main>
      </div>
    </div>
  );
}
