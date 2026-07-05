import WorkflowBuilderClient from "./WorkflowBuilderClient";

export const metadata = {
  title: "Workflow Builder — NovaFlow AI",
  description: "Visual workflow builder and runtime",
};

export default async function WorkflowBuilderPage({ params }) {
  const { id } = await params;
  return <WorkflowBuilderClient workflowId={id} />;
}
