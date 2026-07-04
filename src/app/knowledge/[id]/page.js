import { Suspense } from "react";
import KnowledgeDetailClient from "./KnowledgeDetailClient";
import LiveBackground from "@/components/LiveBackground";

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
          <LiveBackground variant="subtle" showNetwork />
          <span className="relative z-10 text-muted">Loading…</span>
        </div>
      }
    >
      <KnowledgeDetailClient knowledgeId={id} />
    </Suspense>
  );
}
