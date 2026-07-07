"use client";

import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";

export default function WorkspacePageShell({
  user,
  loading = false,
  loadingMessage,
  children,
  maxWidth = "max-w-6xl",
  backgroundActive = false,
}) {
  if (loading || !user) {
    return <WorkspaceLoading message={loadingMessage} />;
  }

  return (
    <div className="workspace-shell relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground active={backgroundActive} />
      <div className="relative z-10">
        <AppHeader user={user} />
        <main className={`workspace-page-main mx-auto ${maxWidth} px-4 py-10 sm:px-6 sm:py-12`}>
          {children}
        </main>
      </div>
    </div>
  );
}
