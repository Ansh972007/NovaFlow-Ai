import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const ModelLabClient = dynamic(() => import("./ModelLabClient"), {
  loading: () => <WorkspacePageLoading message="Loading Model Lab…" />,
});

export const metadata = {
  title: "Model Lab — NovaFlow AI",
  description: "Train models from knowledge and auto-evaluate",
};

export default function ModelLabPage() {
  return <ModelLabClient />;
}
