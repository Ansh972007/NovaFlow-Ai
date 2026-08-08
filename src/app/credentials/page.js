import { Suspense } from "react";
import CredentialsClient from "./CredentialsClient";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

export const metadata = {
  title: "Credentials — NovaFlow AI",
  description: "API keys, models, Gmail, Telegram, and integration secrets",
};

export default function CredentialsPage() {
  return (
    <Suspense fallback={<WorkspacePageLoading message="Loading credentials…" />}>
      <CredentialsClient />
    </Suspense>
  );
}
