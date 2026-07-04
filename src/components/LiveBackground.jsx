"use client";

import { motion, useMotionTemplate, useMotionValue, useSpring } from "framer-motion";
import { useEffect } from "react";
import LiveCanvas from "./LiveCanvas";

export default function LiveBackground({
  variant = "light",
  mouseTracking = false,
  showGrid = true,
  showOrbs = true,
  showNetwork = true,
  className = "",
}) {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 60, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 60, damping: 20 });

  const spotlight = useMotionTemplate`radial-gradient(1000px circle at ${springX}px ${springY}px, ${
    variant === "dark" ? "rgba(255,255,255,0.14)" : "rgba(255,255,255,0.85)"
  }, transparent 60%)`;

  const spotlightCore = useMotionTemplate`radial-gradient(400px circle at ${springX}px ${springY}px, ${
    variant === "dark" ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"
  }, transparent 70%)`;

  useEffect(() => {
    if (!mouseTracking) return;
    const handler = (e) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };
    window.addEventListener("mousemove", handler, { passive: true });
    return () => window.removeEventListener("mousemove", handler);
  }, [mouseTracking, mouseX, mouseY]);

  const isDark = variant === "dark";
  const isSubtle = variant === "subtle";

  return (
    <div className={`absolute inset-0 overflow-hidden ${className}`} aria-hidden>
      <div
        className={`absolute inset-0 ${
          isDark
            ? "bg-[#0a0a0a]"
            : isSubtle
              ? "bg-gradient-to-br from-white via-[#fcfcfc] to-[#f5f5f5]"
              : "bg-gradient-to-br from-[#ffffff] via-[#fafafa] to-[#f3f3f3]"
        }`}
      />

      <div className={`live-mesh absolute inset-0 ${isDark ? "live-mesh-dark" : isSubtle ? "live-mesh-subtle" : "live-mesh-light"}`} />

      {showOrbs && (
        <>
          <motion.div
            animate={{ x: [0, 80, 20, 0], y: [0, -50, 30, 0], scale: [1, 1.2, 1.05, 1] }}
            transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
            className={`absolute -left-[10%] -top-[10%] h-[55vh] w-[55vh] rounded-full blur-[100px] ${
              isDark ? "bg-white/[0.1]" : "bg-neutral-300/55"
            }`}
          />
          <motion.div
            animate={{ x: [0, -70, -20, 0], y: [0, 60, -20, 0], scale: [1, 1.15, 0.95, 1] }}
            transition={{ duration: 35, repeat: Infinity, ease: "easeInOut", delay: 4 }}
            className={`absolute -right-[5%] top-[10%] h-[60vh] w-[60vh] rounded-full blur-[120px] ${
              isDark ? "bg-white/[0.08]" : "bg-neutral-200/60"
            }`}
          />
          <motion.div
            animate={{ x: [0, 40, -30, 0], y: [0, -40, 50, 0] }}
            transition={{ duration: 28, repeat: Infinity, ease: "easeInOut", delay: 8 }}
            className={`absolute bottom-[-5%] left-[20%] h-[45vh] w-[45vh] rounded-full blur-[90px] ${
              isDark ? "bg-white/[0.09]" : "bg-neutral-400/35"
            }`}
          />
          <motion.div
            animate={{ x: [0, -30, 40, 0], y: [0, 30, -20, 0], opacity: [0.5, 0.85, 0.6, 0.5] }}
            transition={{ duration: 22, repeat: Infinity, ease: "easeInOut", delay: 2 }}
            className={`absolute left-[40%] top-[45%] h-[35vh] w-[35vh] rounded-full blur-[90px] ${
              isDark ? "bg-white/[0.06]" : "bg-white/80"
            }`}
          />
        </>
      )}

      {showNetwork && (
        <LiveCanvas variant={variant} mouseTracking={mouseTracking} />
      )}

      {showGrid && (
        <div
          className={`absolute inset-0 ${isDark ? "grid-bg-dark" : "grid-bg"} ${
            isSubtle ? "opacity-45" : "opacity-65"
          }`}
        />
      )}

      <motion.div
        animate={{ x: ["-15%", "15%", "-15%"], opacity: [0.35, 0.65, 0.35] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
        className={`absolute -top-1/2 left-0 h-[200%] w-[200%] -rotate-6 blur-[70px] ${
          isDark
            ? "bg-gradient-to-r from-transparent via-white/[0.1] to-transparent"
            : "bg-gradient-to-r from-transparent via-neutral-300/40 to-transparent"
        }`}
      />
      <motion.div
        animate={{ x: ["10%", "-10%", "10%"], opacity: [0.25, 0.5, 0.25] }}
        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut", delay: 5 }}
        className={`absolute -bottom-1/2 right-0 h-[200%] w-[200%] rotate-12 blur-[80px] ${
          isDark
            ? "bg-gradient-to-l from-transparent via-white/[0.07] to-transparent"
            : "bg-gradient-to-l from-transparent via-neutral-200/50 to-transparent"
        }`}
      />

      {mouseTracking && (
        <>
          <motion.div className="absolute inset-0" style={{ background: spotlight }} />
          <motion.div className="absolute inset-0 mix-blend-multiply" style={{ background: spotlightCore }} />
        </>
      )}

      <div
        className={`absolute inset-0 ${
          isDark
            ? "bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.35)_100%)]"
            : "bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(240,240,240,0.4)_100%)]"
        }`}
      />
    </div>
  );
}
