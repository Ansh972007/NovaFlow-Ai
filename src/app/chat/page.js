import { Suspense } from "react";
import ChatPageClient from "./ChatPageClient";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

export const metadata = {
  title: "Build — NovaFlow AI",
  description: "Conversational workspace composer",
};

export default function ChatPage() {
  return (
    <Suspense fallback={<WorkspacePageLoading />}>
      <ChatPageClient />
    </Suspense>
  );
}
