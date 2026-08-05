import { redirect } from "next/navigation";

export const metadata = {
  title: "Credentials — NovaFlow AI",
  description: "Digests moved to Workflows; secrets live in Credentials",
};

export default function DigestsRedirectPage() {
  redirect("/credentials");
}
