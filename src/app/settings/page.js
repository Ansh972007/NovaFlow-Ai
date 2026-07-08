import { Suspense } from "react";
import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const SettingsClient = dynamic(() => import("./SettingsClient"), {
  loading: () => <WorkspacePageLoading message="Loading settings…" />,
});

export const metadata = {
  title: "Settings — NovaFlow AI",
  description: "Workspace health and configuration",
};

export default function SettingsPage() {
  return (
    <Suspense fallback={<WorkspacePageLoading message="Loading settings…" />}>
      <SettingsClient />
    </Suspense>
  );
}
