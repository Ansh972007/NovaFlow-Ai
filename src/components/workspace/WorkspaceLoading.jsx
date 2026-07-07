"use client";

import { memo } from "react";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";

function WorkspaceLoading({ message = "Loading workspace…" }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-4">
        <div className="relative flex h-12 w-12 items-center justify-center">
          <div className="chat-empty-ring absolute inset-0 rounded-xl" />
          <div className="h-10 w-10 animate-pulse rounded-lg bg-neutral-900/90" />
        </div>
        <p className="text-sm text-neutral-500">{message}</p>
      </div>
    </div>
  );
}

export default memo(WorkspaceLoading);
