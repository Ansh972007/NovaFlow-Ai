import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const ProjectsClient = dynamic(() => import("./ProjectsClient"), {
  loading: () => <WorkspacePageLoading message="Loading projects…" />,
});

export const metadata = {
  title: "Projects — NovaFlow AI",
  description: "Map integrations and workflows to dev projects",
};

export default function ProjectsPage() {
  return <ProjectsClient />;
}
