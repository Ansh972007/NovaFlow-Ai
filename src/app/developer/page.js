import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const DeveloperClient = dynamic(() => import("./DeveloperClient"), {
  loading: () => <WorkspacePageLoading />,
});

export const metadata = {
  title: "API Playground — NovaFlow AI",
  description: "Test NovaFlow API endpoints with your session or API key",
};

export default function DeveloperPage() {
  return <DeveloperClient />;
}
