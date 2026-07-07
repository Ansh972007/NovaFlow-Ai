import { Suspense } from "react";
import ChatPageClient from "./ChatPageClient";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

export const metadata = {
  title: "Chat — NovaFlow AI",
  description: "Chat with your AI assistants",
};

export default function ChatPage() {
  return (
    <Suspense fallback={<WorkspacePageLoading />}>
      <ChatPageClient />
    </Suspense>
  );
}
