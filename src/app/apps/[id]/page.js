import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const AssistantDetailClient = dynamic(() => import("./AssistantDetailClient"), {
  loading: () => <WorkspacePageLoading />,
});

export async function generateMetadata({ params }) {
  const { id } = await params;
  return {
    title: `Assistant — NovaFlow AI`,
    description: `Configure assistant ${id}`,
  };
}

export default async function AssistantDetailPage({ params }) {
  const { id } = await params;
  return <AssistantDetailClient assistantId={id} />;
}
