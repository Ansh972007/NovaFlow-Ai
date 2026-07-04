"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export default function LiveMetric({ label, value, suffix = "", dark = false, animate = true }) {
  const [display, setDisplay] = useState(value);

  useEffect(() => {
    if (!animate) return;
    const timer = setInterval(() => {
      const jitter = Math.floor(Math.random() * 6) - 3;
      setDisplay(Math.max(0, value + jitter));
    }, 2200);
    return () => clearInterval(timer);
  }, [value, animate]);

  return (
    <motion.div
      animate={{ y: [0, dark ? 8 : -8, 0] }}
      transition={{ duration: 5 + Math.random() * 2, repeat: Infinity, ease: "easeInOut" }}
      className={`rounded-2xl border px-4 py-3 shadow-xl ${
        dark
          ? "border-border bg-black text-white"
          : "border-border bg-white/90 backdrop-blur-sm"
      }`}
    >
      <p className={`text-[10px] font-semibold tracking-widest uppercase ${
        dark ? "text-neutral-400" : "text-muted"
      }`}>
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">
        {display}
        {suffix}
      </p>
    </motion.div>
  );
}
