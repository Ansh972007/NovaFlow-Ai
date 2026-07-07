import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const WorkflowBuilderClient = dynamic(() => import("./WorkflowBuilderClient"), {
  loading: () => <WorkspacePageLoading />,
});

export const metadata = {
  title: "Workflow Builder — NovaFlow AI",
  description: "Visual workflow builder and runtime",
};

export default async function WorkflowBuilderPage({ params }) {
  const { id } = await params;
  return <WorkflowBuilderClient workflowId={id} />;
}
