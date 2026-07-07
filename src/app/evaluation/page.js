import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const EvaluationClient = dynamic(() => import("./EvaluationClient"), {
  loading: () => <WorkspacePageLoading />,
});

export default function EvaluationPage() {
  return <EvaluationClient />;
}
