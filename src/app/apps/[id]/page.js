import { redirect } from "next/navigation";

export default async function AppsDetailRedirectPage({ params }) {
  const { id } = await params;
  redirect(`/projects/assistants/${id}`);
}
