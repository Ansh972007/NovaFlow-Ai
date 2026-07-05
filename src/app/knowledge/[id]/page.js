import { Suspense } from "react";
import KnowledgeDetailClient from "./KnowledgeDetailClient";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";

export async function generateMetadata({ params }) {
  const { id } = await params;
  return {
    title: `Knowledge #${id} — NovaFlow AI`,
    description: "Manage documents in your knowledge base",
  };
}

export default async function KnowledgeDetailPage({ params }) {
  const { id } = await params;
  return (
    <Suspense
      fallback={
        <div className="relative flex min-h-screen items-center justify-center">
          <WorkspaceLiveBackground />
          <span className="relative z-10 text-muted">Loading…</span>
        </div>
      }
    >
      <KnowledgeDetailClient knowledgeId={id} />
    </Suspense>
  );
}
