import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const DigestsClient = dynamic(() => import("./DigestsClient"), {
  loading: () => <WorkspacePageLoading message="Loading digests…" />,
});

export const metadata = {
  title: "Digests & Schedules — NovaFlow AI",
  description: "Workspace cron schedules and digest workflows",
};

export default function DigestsPage() {
  return <DigestsClient />;
}
