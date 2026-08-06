"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LandingOrbitRings } from "@/components/landing/LandingGodFrame";

const ease = [0.16, 1, 0.3, 1];

export default function PageLoader() {
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const p1 = setTimeout(() => setPhase(1), 100);
    const p2 = setTimeout(() => setPhase(2), 150);
    const done = setTimeout(() => setLoading(false), 200);
    return () => {
      clearTimeout(p1);
      clearTimeout(p2);
      clearTimeout(done);
    };
  }, []);

  return (
    <AnimatePresence>
      {loading && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.02 }}
          transition={{ duration: 0.7, ease }}
          className="fixed inset-0 z-[200] flex items-center justify-center overflow-hidden bg-white"
        >
          <LandingOrbitRings className="opacity-40" />
          <motion.div
            initial={{ clipPath: "inset(0 0 0 0)" }}
            exit={{ clipPath: "inset(0 0 100% 0)" }}
            transition={{ duration: 0.65, ease }}
            className="absolute inset-0 bg-white"
          />

          <div className="relative flex flex-col items-center gap-7">
            <motion.div
              initial={{ scale: 0.7, opacity: 0, rotate: -8 }}
              animate={{ scale: 1, opacity: 1, rotate: 0 }}
              transition={{ duration: 0.65, ease }}
              className="relative"
            >
              <motion.span
                animate={{ scale: [1, 1.2, 1], opacity: [0.4, 0.15, 0.4] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -inset-4 rounded-full border border-black/10"
              />
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                className="absolute -inset-2 rounded-full border border-dashed border-black/15"
              />
              <span className="relative flex h-16 w-16 items-center justify-center rounded-full bg-black text-xl font-bold text-white shadow-[0_20px_60px_rgba(0,0,0,0.25)]">
                NF
              </span>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.5, ease }}
              className="flex flex-col items-center gap-3"
            >
              <motion.p
                animate={{ opacity: phase >= 1 ? 1 : 0.5 }}
                className="text-sm font-semibold tracking-[0.18em] uppercase"
              >
                NovaFlow AI
              </motion.p>
              <div className="relative h-0.5 w-32 overflow-hidden rounded-full bg-neutral-100">
                <motion.div
                  initial={{ x: "-100%" }}
                  animate={{ x: phase >= 2 ? "0%" : "-60%" }}
                  transition={{ duration: 0.55, ease }}
                  className="h-full w-full bg-gradient-to-r from-black via-neutral-700 to-black"
                />
              </div>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: phase >= 2 ? 0.7 : 0 }}
                className="text-[10px] tracking-[0.25em] text-muted uppercase"
              >
                Initializing workspace
              </motion.p>
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
