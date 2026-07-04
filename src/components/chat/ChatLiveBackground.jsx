"use client";

import { motion, useMotionTemplate, useMotionValue, useSpring } from "framer-motion";
import { useEffect } from "react";

/**
 * Minimal chat ambient — soft white base, gentle black motion.
 * No particles, scan lines, or landing-style neural net.
 */
export default function ChatLiveBackground({ className = "", active = false }) {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 45, damping: 26 });
  const springY = useSpring(mouseY, { stiffness: 45, damping: 26 });

  const glow = useMotionTemplate`radial-gradient(520px circle at ${springX}px ${springY}px, rgba(0,0,0,0.035), transparent 72%)`;

  useEffect(() => {
    const handler = (e) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };
    window.addEventListener("mousemove", handler, { passive: true });
    return () => window.removeEventListener("mousemove", handler);
  }, [mouseX, mouseY]);

  const drift = active ? 22 : 34;

  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden>
      <div className="absolute inset-0 bg-white" />

      <motion.div
        animate={{ x: [0, 36, 8, 0], y: [0, -28, 16, 0], scale: [1, 1.06, 1.02, 1] }}
        transition={{ duration: drift, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -left-[12%] top-[2%] h-[65vh] w-[65vh] rounded-full bg-neutral-300/30 blur-[110px]"
      />
      <motion.div
        animate={{ x: [0, -42, -12, 0], y: [0, 32, -12, 0], scale: [1, 1.08, 0.98, 1] }}
        transition={{ duration: drift + 8, repeat: Infinity, ease: "easeInOut", delay: 3 }}
        className="absolute -right-[8%] top-[18%] h-[58vh] w-[58vh] rounded-full bg-neutral-200/45 blur-[120px]"
      />
      <motion.div
        animate={{ x: [0, 24, -18, 0], y: [0, -20, 28, 0] }}
        transition={{ duration: drift + 4, repeat: Infinity, ease: "easeInOut", delay: 6 }}
        className="absolute bottom-[-6%] left-[28%] h-[48vh] w-[48vh] rounded-full bg-neutral-300/25 blur-[100px]"
      />

      <div className="chat-ambient-grid absolute inset-0" />

      <svg
        className="absolute inset-0 h-full w-full opacity-80"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="xMidYMid slice"
      >
        <motion.g
          animate={{ rotate: 360 }}
          transition={{ duration: active ? 90 : 140, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "500px 500px" }}
        >
          <ellipse
            cx="500"
            cy="500"
            rx="360"
            ry="200"
            fill="none"
            stroke="rgba(0,0,0,0.055)"
            strokeWidth="1"
            transform="rotate(-14 500 500)"
          />
        </motion.g>
        <motion.g
          animate={{ rotate: -360 }}
          transition={{ duration: active ? 110 : 170, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "500px 500px" }}
        >
          <ellipse
            cx="500"
            cy="500"
            rx="280"
            ry="150"
            fill="none"
            stroke="rgba(0,0,0,0.04)"
            strokeWidth="0.75"
            transform="rotate(22 500 500)"
          />
        </motion.g>
        <motion.circle
          cx="500"
          cy="500"
          fill="none"
          stroke="rgba(0,0,0,0.07)"
          strokeWidth="1"
          strokeDasharray="3 10"
          animate={{ r: [125, 145, 125], opacity: [0.35, 0.65, 0.35] }}
          transition={{ duration: active ? 7 : 11, repeat: Infinity, ease: "easeInOut" }}
        />
      </svg>

      <motion.div className="absolute inset-0" style={{ background: glow }} />

      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_45%,rgba(255,255,255,0.65)_100%)]" />
    </div>
  );
}
