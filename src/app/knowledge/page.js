import { Suspense } from "react";
import KnowledgeListClient from "./KnowledgeListClient";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";

export const metadata = {
  title: "Knowledge — NovaFlow AI",
  description: "Manage knowledge bases and documents",
};

export default function KnowledgePage() {
  return (
    <Suspense
      fallback={
        <div className="relative flex min-h-screen items-center justify-center">
          <WorkspaceLiveBackground />
          <span className="relative z-10 text-muted">Loading knowledge…</span>
        </div>
      }
    >
      <KnowledgeListClient />
    </Suspense>
  );
}
