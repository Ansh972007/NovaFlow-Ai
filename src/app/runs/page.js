import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const RunsClient = dynamic(() => import("./RunsClient"), {
  loading: () => <WorkspacePageLoading message="Loading runs…" />,
});

export const metadata = {
  title: "Runs — NovaFlow AI",
  description: "Workspace workflow run history",
};

export default function RunsPage() {
  return <RunsClient />;
}
