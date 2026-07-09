import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const DocsClient = dynamic(() => import("./DocsClient"), {
  loading: () => <WorkspacePageLoading message="Loading documentation…" />,
});

export const metadata = {
  title: "Template Guide — NovaFlow AI",
  description: "Complete documentation for workflows, digests, prompts, and node connections",
};

export default function DocsPage() {
  return <DocsClient />;
}
