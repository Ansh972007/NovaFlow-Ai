import dynamic from "next/dynamic";
import { Suspense } from "react";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const ProjectsClient = dynamic(() => import("./ProjectsClient"), {
  loading: () => <WorkspacePageLoading message="Loading projects…" />,
});

export const metadata = {
  title: "Projects — NovaFlow AI",
  description: "Projects, integrations, workflows, and chat assistants",
};

export default function ProjectsPage() {
  return (
    <Suspense fallback={<WorkspacePageLoading message="Loading projects…" />}>
      <ProjectsClient />
    </Suspense>
  );
}
