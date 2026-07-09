"use client";

import { memo } from "react";
import { motion } from "framer-motion";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";

const ease = [0.16, 1, 0.3, 1];

function WorkspaceLoading({ message = "Loading workspace…" }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <WorkspaceLiveBackground active />
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-5">
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.55, ease }}
          className="relative flex h-14 w-14 items-center justify-center"
        >
          <motion.span
            animate={{ rotate: 360 }}
            transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
            className="absolute inset-0 rounded-2xl border border-dashed border-black/15"
          />
          <motion.span
            animate={{ scale: [1, 1.08, 1], opacity: [0.35, 0.15, 0.35] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
            className="absolute inset-1 rounded-xl bg-black/5"
          />
          <span className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-black text-xs font-bold text-white">
            NF
          </span>
        </motion.div>
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.45, ease }}
          className="text-sm text-neutral-500"
        >
          {message}
        </motion.p>
        <div className="h-0.5 w-24 overflow-hidden rounded-full bg-neutral-100">
          <motion.div
            animate={{ x: ["-100%", "100%"] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
            className="h-full w-1/2 bg-neutral-800"
          />
        </div>
      </div>
    </div>
  );
}

export default memo(WorkspaceLoading);
