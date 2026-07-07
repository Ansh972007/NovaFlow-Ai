"use client";

import { memo, useEffect } from "react";
import LiveCanvas from "./LiveCanvas";
import { enableMouseCss } from "@/lib/runtime/mouseCss";

function LiveBackground({
  variant = "light",
  mouseTracking = false,
  showGrid = true,
  showOrbs = true,
  showNetwork = true,
  className = "",
}) {
  useEffect(() => {
    if (!mouseTracking) return undefined;
    return enableMouseCss();
  }, [mouseTracking]);

  const isDark = variant === "dark";
  const isSubtle = variant === "subtle";

  return (
    <div className={`nf-live-bg-root absolute inset-0 overflow-hidden ${className}`} aria-hidden>
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
          <div
            className={`nf-bg-orb-1 absolute -left-[10%] -top-[10%] h-[55vh] w-[55vh] rounded-full blur-[100px] ${
              isDark ? "bg-white/[0.1]" : "bg-neutral-300/55"
            }`}
          />
          <div
            className={`nf-bg-orb-2 absolute -right-[5%] top-[10%] h-[60vh] w-[60vh] rounded-full blur-[120px] ${
              isDark ? "bg-white/[0.08]" : "bg-neutral-200/60"
            }`}
          />
          <div
            className={`nf-bg-orb-3 absolute bottom-[-5%] left-[20%] h-[45vh] w-[45vh] rounded-full blur-[90px] ${
              isDark ? "bg-white/[0.09]" : "bg-neutral-400/35"
            }`}
          />
          <div
            className={`nf-bg-orb-4 absolute left-[40%] top-[45%] h-[35vh] w-[35vh] rounded-full blur-[90px] ${
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

      <div
        className={`nf-bg-sweep-1 absolute -top-1/2 left-0 h-[200%] w-[200%] -rotate-6 blur-[70px] ${
          isDark
            ? "bg-gradient-to-r from-transparent via-white/[0.1] to-transparent"
            : "bg-gradient-to-r from-transparent via-neutral-300/40 to-transparent"
        }`}
      />
      <div
        className={`nf-bg-sweep-2 absolute -bottom-1/2 right-0 h-[200%] w-[200%] rotate-12 blur-[80px] ${
          isDark
            ? "bg-gradient-to-l from-transparent via-white/[0.07] to-transparent"
            : "bg-gradient-to-l from-transparent via-neutral-200/50 to-transparent"
        }`}
      />

      {mouseTracking && (
        <>
          <div
            className={`absolute inset-0 ${isDark ? "nf-spotlight-landing-dark" : "nf-spotlight-landing"}`}
            style={
              isDark
                ? {
                    background:
                      "radial-gradient(1000px circle at var(--nf-mx, 50%) var(--nf-my, 50%), rgba(255,255,255,0.14), transparent 60%)",
                  }
                : undefined
            }
          />
          <div
            className={`absolute inset-0 ${isDark ? "" : "nf-spotlight-landing-core"}`}
            style={
              isDark
                ? {
                    background:
                      "radial-gradient(400px circle at var(--nf-mx, 50%) var(--nf-my, 50%), rgba(255,255,255,0.08), transparent 70%)",
                    mixBlendMode: "multiply",
                  }
                : undefined
            }
          />
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

export default memo(LiveBackground);
