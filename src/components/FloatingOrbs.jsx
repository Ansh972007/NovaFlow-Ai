"use client";

import { motion } from "framer-motion";

export default function FloatingOrbs() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <motion.div
        animate={{ x: [0, 30, 0], y: [0, -20, 0] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -left-32 top-20 h-72 w-72 rounded-full bg-neutral-200/60 blur-[80px]"
      />
      <motion.div
        animate={{ x: [0, -40, 0], y: [0, 30, 0] }}
        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut", delay: 2 }}
        className="absolute -right-20 top-1/3 h-96 w-96 rounded-full bg-neutral-100 blur-[100px]"
      />
      <motion.div
        animate={{ x: [0, 20, 0], y: [0, 40, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut", delay: 4 }}
        className="absolute bottom-0 left-1/3 h-64 w-64 rounded-full bg-neutral-200/40 blur-[90px]"
      />
    </div>
  );
}
