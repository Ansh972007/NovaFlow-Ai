"use client";

import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import { ease } from "@/lib/motion/workspace";

export default function WorkspacePageShell({
  user,
  loading = false,
  loadingMessage,
  children,
  maxWidth = "max-w-6xl",
  backgroundActive = true,
}) {
  if (loading || !user) {
    return <WorkspaceLoading message={loadingMessage} />;
  }

  return (
    <div className="workspace-shell relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground active={backgroundActive} />
      <div className="relative z-10">
        <AppHeader user={user} />
        <motion.main
          initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.65, ease }}
          className={`workspace-page-main mx-auto ${maxWidth} px-4 py-10 sm:px-6 sm:py-12`}
        >
          {children}
        </motion.main>
      </div>
    </div>
  );
}
