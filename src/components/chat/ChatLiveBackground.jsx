"use client";

import { motion, useMotionTemplate, useMotionValue, useSpring } from "framer-motion";
import { useEffect } from "react";
import ChatFlowCanvas from "./ChatFlowCanvas";

/**
 * Chat live bg — flowing streams + curved neural web (god-tier, distinct from landing).
 */
export default function ChatLiveBackground({ className = "", active = false, variant = "full" }) {
  const isFull = variant !== "light";
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 60, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 60, damping: 20 });

  const spotlight = useMotionTemplate`radial-gradient(900px circle at ${springX}px ${springY}px, rgba(255,255,255,0.75), transparent 58%)`;
  const spotlightCore = useMotionTemplate`radial-gradient(380px circle at ${springX}px ${springY}px, rgba(0,0,0,0.09), transparent 68%)`;

  useEffect(() => {
    if (!isFull) return undefined;
    let raf = 0;
    let latest = null;
    const flush = () => {
      raf = 0;
      if (!latest) return;
      mouseX.set(latest.clientX);
      mouseY.set(latest.clientY);
    };
    const handler = (e) => {
      latest = e;
      if (!raf) raf = requestAnimationFrame(flush);
    };
    window.addEventListener("mousemove", handler, { passive: true });
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", handler);
    };
  }, [mouseX, mouseY, isFull]);

  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden>
      <div className="absolute inset-0 bg-gradient-to-br from-[#ffffff] via-[#fafafa] to-[#f3f3f3]" />

      <div className="live-mesh live-mesh-light absolute inset-0 opacity-50" />

      {isFull && <ChatFlowCanvas active={active} />}

      {isFull ? (
        <>
          <motion.div
            animate={{ x: [0, 80, 20, 0], y: [0, -50, 30, 0], scale: [1, 1.15, 1.05, 1] }}
            transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -left-[10%] -top-[10%] h-[50vh] w-[50vh] rounded-full bg-neutral-300/40 blur-[100px]"
          />
          <motion.div
            animate={{ x: [0, -60, -15, 0], y: [0, 45, -15, 0], scale: [1, 1.12, 0.98, 1] }}
            transition={{ duration: 32, repeat: Infinity, ease: "easeInOut", delay: 5 }}
            className="absolute -right-[5%] top-[12%] h-[55vh] w-[55vh] rounded-full bg-neutral-200/50 blur-[110px]"
          />
          <motion.div
            animate={{ x: ["-15%", "15%", "-15%"], opacity: active ? [0.4, 0.7, 0.4] : [0.28, 0.55, 0.28] }}
            transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -top-1/2 left-0 h-[200%] w-[200%] -rotate-6 bg-gradient-to-r from-transparent via-neutral-300/35 to-transparent blur-[65px]"
          />
          <motion.div
            animate={{ x: ["10%", "-10%", "10%"], opacity: active ? [0.3, 0.55, 0.3] : [0.2, 0.42, 0.2] }}
            transition={{ duration: 22, repeat: Infinity, ease: "easeInOut", delay: 4 }}
            className="absolute -bottom-1/2 right-0 h-[200%] w-[200%] rotate-12 bg-gradient-to-l from-transparent via-neutral-200/45 to-transparent blur-[75px]"
          />
        </>
      ) : (
        <>
          <div className="absolute -left-[10%] -top-[10%] h-[45vh] w-[45vh] rounded-full bg-neutral-300/30 blur-[100px]" />
          <div className="absolute -right-[5%] top-[12%] h-[50vh] w-[50vh] rounded-full bg-neutral-200/35 blur-[110px]" />
        </>
      )}

      {isFull && (
        <>
          <motion.div className="absolute inset-0" style={{ background: spotlight }} />
          <motion.div className="absolute inset-0 mix-blend-multiply" style={{ background: spotlightCore }} />
        </>
      )}

      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_60%,rgba(240,240,240,0.35)_100%)]" />
    </div>
  );
}
