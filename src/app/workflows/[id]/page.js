import dynamic from "next/dynamic";
import { notFound } from "next/navigation";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const WorkflowBuilderClient = dynamic(() => import("./WorkflowBuilderClient"), {
  loading: () => <WorkspacePageLoading />,
});

export const metadata = {
  title: "Workflow Builder — NovaFlow AI",
  description: "Visual workflow builder and runtime",
};

function isValidWorkflowId(id) {
  const safe = String(id ?? "").trim();
  return Boolean(safe && safe !== "undefined" && safe !== "null");
}

export default async function WorkflowBuilderPage({ params }) {
  const { id } = await params;
  if (!isValidWorkflowId(id)) {
    notFound();
  }
  return <WorkflowBuilderClient workflowId={id} />;
}
