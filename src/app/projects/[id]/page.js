import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const ProjectDetailClient = dynamic(() => import("./ProjectDetailClient"), {
  loading: () => <WorkspacePageLoading message="Loading project…" />,
});

export const metadata = {
  title: "Project — NovaFlow AI",
};

export default async function ProjectDetailPage({ params }) {
  const { id } = await params;
  return <ProjectDetailClient projectId={id} />;
}
