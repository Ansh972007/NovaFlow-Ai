import { redirect } from "next/navigation";

export const metadata = {
  title: "Projects — NovaFlow AI",
  description: "Assistants moved into Projects",
};

export default function AppsRedirectPage() {
  redirect("/projects?tab=assistants");
}
