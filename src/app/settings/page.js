import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const SettingsClient = dynamic(() => import("./SettingsClient"), {
  loading: () => <WorkspacePageLoading />,
});

export const metadata = {
  title: "Settings — NovaFlow AI",
  description: "Workspace health and configuration",
};

export default function SettingsPage() {
  return <SettingsClient />;
}
