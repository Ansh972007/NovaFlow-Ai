"use client";

import { memo, useEffect } from "react";
import ChatFlowCanvas from "./ChatFlowCanvas";
import { enableMouseCss } from "@/lib/runtime/mouseCss";

function ChatLiveBackground({ className = "", active = false, variant = "full" }) {
  const isFull = variant !== "light";

  useEffect(() => {
    if (!isFull) return undefined;
    return enableMouseCss();
  }, [isFull]);

  return (
    <div
      className={`nf-live-bg-root pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden
    >
      <div className="absolute inset-0 bg-gradient-to-br from-[#ffffff] via-[#fafafa] to-[#f3f3f3]" />

      <div className="live-mesh live-mesh-light absolute inset-0 opacity-50" />

      {isFull && <ChatFlowCanvas active={active} />}

      {isFull ? (
        <>
          <div className="nf-bg-orb-1 absolute -left-[10%] -top-[10%] h-[50vh] w-[50vh] rounded-full bg-neutral-300/40 blur-[100px]" />
          <div className="nf-bg-orb-2 absolute -right-[5%] top-[12%] h-[55vh] w-[55vh] rounded-full bg-neutral-200/50 blur-[110px]" />
          <div
            className={`nf-bg-sweep-1 absolute -top-1/2 left-0 h-[200%] w-[200%] -rotate-6 bg-gradient-to-r from-transparent via-neutral-300/35 to-transparent blur-[65px] ${active ? "nf-bg-active" : ""}`}
          />
          <div
            className={`nf-bg-sweep-2 absolute -bottom-1/2 right-0 h-[200%] w-[200%] rotate-12 bg-gradient-to-l from-transparent via-neutral-200/45 to-transparent blur-[75px] ${active ? "nf-bg-active" : ""}`}
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
          <div className="nf-spotlight-workspace absolute inset-0" />
          <div className="nf-spotlight-workspace-core absolute inset-0" />
        </>
      )}

      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_60%,rgba(240,240,240,0.35)_100%)]" />
    </div>
  );
}

export default memo(ChatLiveBackground);
