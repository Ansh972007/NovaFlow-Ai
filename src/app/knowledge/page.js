import { Suspense } from "react";
import KnowledgeListClient from "./KnowledgeListClient";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

export const metadata = {
  title: "Knowledge — NovaFlow AI",
  description: "Manage knowledge bases and documents",
};

export default function KnowledgePage() {
  return (
    <Suspense fallback={<WorkspacePageLoading message="Loading knowledge…" />}>
      <KnowledgeListClient />
    </Suspense>
  );
}
