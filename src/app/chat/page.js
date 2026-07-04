import { Suspense } from "react";
import ChatPageClient from "./ChatPageClient";

export const metadata = {
  title: "Chat — NovaFlow AI",
  description: "Chat with your AI assistants",
};

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-muted">
          Loading chat…
        </div>
      }
    >
      <ChatPageClient />
    </Suspense>
  );
}
