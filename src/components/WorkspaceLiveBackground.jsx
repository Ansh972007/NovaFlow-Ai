"use client";

import CursorGlow from "@/components/CursorGlow";
import ChatLiveBackground from "@/components/chat/ChatLiveBackground";

/** Shared live flow background for workspace pages (dashboard, knowledge, apps, etc.). */
export default function WorkspaceLiveBackground({ active = false, className = "fixed inset-0 z-0" }) {
  return (
    <>
      <ChatLiveBackground className={className} active={active} variant="full" />
      <CursorGlow />
    </>
  );
}
