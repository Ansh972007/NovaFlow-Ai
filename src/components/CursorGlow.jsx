"use client";

import { memo, useEffect } from "react";
import { enableMouseCss } from "@/lib/runtime/mouseCss";

function CursorGlow() {
  useEffect(() => enableMouseCss(), []);

  return (
    <>
      <div
        className="nf-cursor-glow-soft pointer-events-none fixed inset-0 z-[5] hidden md:block"
        aria-hidden
      />
      <div
        className="nf-cursor-glow-ring pointer-events-none fixed inset-0 z-[5] hidden md:block"
        aria-hidden
      />
    </>
  );
}

export default memo(CursorGlow);
