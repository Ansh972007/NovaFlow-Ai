import AssistantDetailClient from "./AssistantDetailClient";

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
