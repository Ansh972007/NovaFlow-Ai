"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const activities = [
  { type: "inference", text: "GPT-4o inference completed", ms: "38ms" },
  { type: "rag", text: "Knowledge base indexed 1,247 docs", ms: null },
  { type: "deploy", text: "Assistant deployed to production", ms: null },
  { type: "stream", text: "Streaming response to user", ms: "live" },
  { type: "workflow", text: "Workflow executed successfully", ms: "1.2s" },
  { type: "embed", text: "Embeddings generated for batch", ms: "156ms" },
];

export default function LiveAIActivity() {
  const [index, setIndex] = useState(0);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const activityTimer = setInterval(() => {
      setIndex((i) => (i + 1) % activities.length);
    }, 3500);
    return () => clearInterval(activityTimer);
  }, []);

  useEffect(() => {
    const tickTimer = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(tickTimer);
  }, []);

  const current = activities[index];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1, duration: 0.6 }}
      className="mx-auto mt-8 flex max-w-md flex-col items-center gap-3"
    >
      <div className="flex w-full items-center gap-3 rounded-2xl border border-border bg-white/85 px-4 py-3 shadow-md backdrop-blur-xl">
        <NeuralPulse />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-40" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
            </span>
            <span className="text-[10px] font-bold tracking-widest text-green-600 uppercase">
              AI Live
            </span>
            <span className="text-[10px] tabular-nums text-muted-light">
              {String(Math.floor(tick / 3600)).padStart(2, "0")}:
              {String(Math.floor((tick % 3600) / 60)).padStart(2, "0")}:
              {String(tick % 60).padStart(2, "0")}
            </span>
          </div>
          <AnimatePresence mode="wait">
            <motion.p
              key={index}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.3 }}
              className="mt-1 truncate text-xs text-muted"
            >
              {current.text}
              {current.ms && (
                <span className="ml-2 font-mono text-[10px] text-foreground">
                  {current.ms}
                </span>
              )}
            </motion.p>
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

function NeuralPulse() {
  const nodes = [
    { cx: 12, cy: 12, r: 3 },
    { cx: 28, cy: 6, r: 2.5 },
    { cx: 28, cy: 18, r: 2.5 },
    { cx: 44, cy: 12, r: 3 },
  ];
  const edges = [[0, 1], [0, 2], [1, 3], [2, 3]];

  return (
    <svg width="48" height="24" viewBox="0 0 48 24" className="shrink-0">
      {edges.map(([a, b], i) => (
        <motion.line
          key={i}
          x1={nodes[a].cx}
          y1={nodes[a].cy}
          x2={nodes[b].cx}
          y2={nodes[b].cy}
          stroke="currentColor"
          strokeWidth="0.5"
          className="text-neutral-300"
          animate={{ opacity: [0.3, 0.9, 0.3] }}
          transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
        />
      ))}
      {nodes.map((node, i) => (
        <motion.circle
          key={i}
          cx={node.cx}
          cy={node.cy}
          r={node.r}
          fill="currentColor"
          className="text-black"
          animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </svg>
  );
}

export function LiveAIGlobe() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {[...Array(10)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute h-[2px] rounded-full bg-gradient-to-r from-transparent via-black/20 to-transparent shadow-[0_0_12px_rgba(0,0,0,0.08)]"
          style={{
            top: `${8 + i * 9}%`,
            width: `${25 + (i % 4) * 18}%`,
            left: `${(i * 11) % 50}%`,
          }}
          animate={{
            x: ["-120%", "220%"],
            opacity: [0, 0.8, 0],
            scaleX: [0.6, 1, 0.6],
          }}
          transition={{
            duration: 6 + i * 1.2,
            repeat: Infinity,
            ease: "linear",
            delay: i * 0.8,
          }}
        />
      ))}
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={`v-${i}`}
          className="absolute w-px bg-gradient-to-b from-transparent via-black/10 to-transparent"
          style={{
            left: `${20 + i * 15}%`,
            height: "40%",
            top: `${10 + (i % 3) * 20}%`,
          }}
          animate={{ opacity: [0.1, 0.4, 0.1], scaleY: [0.8, 1.2, 0.8] }}
          transition={{ duration: 4 + i, repeat: Infinity, ease: "easeInOut", delay: i * 0.5 }}
        />
      ))}
    </div>
  );
}
