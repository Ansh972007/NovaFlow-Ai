"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import ChatSidebar from "@/components/chat/ChatSidebar";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";
import ChatLiveBackground from "@/components/chat/ChatLiveBackground";
import CursorGlow from "@/components/CursorGlow";
import { useAssistantChat } from "@/hooks/useAssistantChat";
import { getOnlineApps, getAssistants, getAssistantInfo, FLOW_TYPE } from "@/lib/api/apps";
import { getUserInfo, logout } from "@/lib/api/auth";
import {
  getSessionsForApp,
  getSessionMessages,
  upsertSession,
} from "@/lib/chat/storage";
import { generateId } from "@/lib/utils";

function ChatLoading() {
  return (
    <div className="chat-shell relative flex min-h-screen items-center justify-center overflow-hidden">
      <ChatLiveBackground variant="full" />
      <CursorGlow />
      <div className="relative z-10 flex flex-col items-center gap-4">
        <div className="relative flex h-12 w-12 items-center justify-center">
          <div className="chat-empty-ring absolute inset-0 rounded-xl" />
          <div className="h-10 w-10 animate-pulse rounded-lg bg-neutral-900/90" />
        </div>
        <p className="text-sm text-neutral-500">Loading workspace…</p>
      </div>
    </div>
  );
}

export default function ChatPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const appIdParam = searchParams.get("app");
  const sessionParam = searchParams.get("session");

  const [user, setUser] = useState(null);
  const [apps, setApps] = useState([]);
  const [selectedApp, setSelectedApp] = useState(null);
  const [sessionId, setSessionId] = useState(sessionParam || "");
  const [sessions, setSessions] = useState([]);
  const [initialMessages, setInitialMessages] = useState([]);
  const [loadingApps, setLoadingApps] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [ragCount, setRagCount] = useState(0);

  const { messages, streaming, error, sendMessage, stop } = useAssistantChat({
    app: selectedApp,
    sessionId,
    initialMessages,
  });

  const loadApps = useCallback(async () => {
    setLoadingApps(true);
    try {
      let list = await getOnlineApps();
      if (!list?.length) {
        const assistants = await getAssistants();
        list = (assistants || []).map((a) => ({
          ...a,
          flow_type: FLOW_TYPE.ASSISTANT,
        }));
      }
      setApps(list || []);
      return list || [];
    } catch {
      setApps([]);
      return [];
    } finally {
      setLoadingApps(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"))
      .finally(() => setAuthChecked(true));
  }, [router]);

  useEffect(() => {
    if (!authChecked || !user) return;
    loadApps().then((list) => {
      if (!list.length) return;
      const app = list.find((a) => String(a.id) === String(appIdParam)) || list[0];
      setSelectedApp(app);
    });
  }, [authChecked, user, loadApps, appIdParam]);

  useEffect(() => {
    if (!selectedApp?.id) {
      setRagCount(0);
      return;
    }
    getAssistantInfo(selectedApp.id)
      .then((info) => {
        const ids = info?.knowledge_ids || info?.knowledge_list?.map((k) => k.id) || [];
        setRagCount(ids.length);
      })
      .catch(() => setRagCount(0));
  }, [selectedApp?.id]);

  useEffect(() => {
    if (!selectedApp) return;
    const appSessions = getSessionsForApp(selectedApp.id);
    setSessions(appSessions);

    if (sessionParam && appSessions.some((s) => s.id === sessionParam)) {
      setSessionId(sessionParam);
      setInitialMessages(getSessionMessages(sessionParam));
    } else if (appSessions.length > 0) {
      setSessionId(appSessions[0].id);
      setInitialMessages(getSessionMessages(appSessions[0].id));
    } else {
      const newId = generateId();
      upsertSession({
        id: newId,
        appId: selectedApp.id,
        appName: selectedApp.name,
        flowType: selectedApp.flow_type,
        title: "New chat",
        messages: [],
      });
      setSessionId(newId);
      setInitialMessages([]);
      setSessions(getSessionsForApp(selectedApp.id));
      router.replace(`/chat?app=${selectedApp.id}&session=${newId}`);
    }
  }, [selectedApp?.id, sessionParam, router]);

  const handleSelectApp = (app) => {
    setSelectedApp(app);
    const newId = generateId();
    upsertSession({
      id: newId,
      appId: app.id,
      appName: app.name,
      flowType: app.flow_type,
      title: "New chat",
      messages: [],
    });
    setSessions(getSessionsForApp(app.id));
    setSessionId(newId);
    setInitialMessages([]);
    router.push(`/chat?app=${app.id}&session=${newId}`);
  };

  const handleSelectSession = (session) => {
    setSessionId(session.id);
    setInitialMessages(session.messages || getSessionMessages(session.id));
    router.push(`/chat?app=${session.appId}&session=${session.id}`);
  };

  const handleNewChat = () => {
    if (!selectedApp) return;
    const newId = generateId();
    upsertSession({
      id: newId,
      appId: selectedApp.id,
      appName: selectedApp.name,
      flowType: selectedApp.flow_type,
      title: "New chat",
      messages: [],
    });
    setSessions(getSessionsForApp(selectedApp.id));
    setSessionId(newId);
    setInitialMessages([]);
    router.push(`/chat?app=${selectedApp.id}&session=${newId}`);
  };

  async function handleLogout() {
    try {
      await logout();
    } catch {
      /* ignore */
    }
    localStorage.removeItem("nf_token");
    router.push("/login");
  }

  const headerTitle = useMemo(() => selectedApp?.name || "Chat", [selectedApp]);

  function exportTranscript() {
    if (!messages?.length) return;
    const lines = messages.map((m) => `**${m.role === "user" ? "You" : "Assistant"}:** ${m.content || ""}`);
    const md = `# ${headerTitle}\n\n${lines.join("\n\n")}\n`;
    const blob = new Blob([md], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `novaflow-chat-${sessionId || "session"}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  if (!authChecked) {
    return <ChatLoading />;
  }

  return (
    <div className="chat-shell relative flex h-[100dvh] overflow-hidden">
      <ChatLiveBackground className="fixed inset-0 z-0" active={streaming} variant="full" />
      <CursorGlow />

      <ChatSidebar
        apps={apps}
        sessions={sessions}
        selectedAppId={selectedApp?.id}
        selectedSessionId={sessionId}
        onSelectApp={handleSelectApp}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        loading={loadingApps}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        userName={user?.user_name}
        onLogout={handleLogout}
      />

      <div className="chat-main-panel relative z-10 flex min-h-0 min-w-0 flex-1 flex-col">
        <motion.header
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="chat-header flex h-14 shrink-0 items-center justify-between px-3 sm:px-5"
        >
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-neutral-500 transition-colors hover:bg-neutral-100 md:hidden"
              aria-label="Open menu"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-semibold tracking-tight text-neutral-900">{headerTitle}</p>
                {ragCount > 0 && (
                  <Link
                    href={selectedApp ? `/apps/${selectedApp.id}` : "/apps"}
                    className="workspace-badge-live hidden shrink-0 sm:inline-flex"
                    title="Knowledge bases linked for RAG"
                  >
                    RAG · {ragCount}
                  </Link>
                )}
              </div>
              {streaming && (
                <p className="flex items-center gap-1.5 text-[10px] font-medium text-neutral-500">
                  <span className="chat-status-dot h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  Responding…
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-0.5">
            {messages.length > 0 && (
              <button
                type="button"
                onClick={exportTranscript}
                className="chat-header-link hidden rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-500 hover:bg-neutral-100/80 hover:text-neutral-900 sm:inline"
              >
                Export
              </button>
            )}
            <Link
              href={selectedApp ? `/apps/${selectedApp.id}` : "/apps"}
              className="chat-header-link hidden rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-500 hover:bg-neutral-100/80 hover:text-neutral-900 sm:inline"
            >
              Configure
            </Link>
            <Link
              href="/dashboard"
              className="chat-header-link hidden rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-500 hover:bg-neutral-100/80 hover:text-neutral-900 sm:inline"
            >
              Dashboard
            </Link>
            <Link
              href="/knowledge"
              className="chat-header-link hidden rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-500 hover:bg-neutral-100/80 hover:text-neutral-900 sm:inline"
            >
              Knowledge
            </Link>
            <Link
              href="/"
              className="chat-header-link rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-500 hover:bg-neutral-100/80 hover:text-neutral-900"
            >
              Home
            </Link>
          </div>
        </motion.header>

        {!selectedApp && !loadingApps ? (
          <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
            <div className="relative mb-5 flex h-14 w-14 items-center justify-center">
              <div className="chat-empty-ring absolute inset-0 rounded-xl" />
              <div className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-900 text-sm font-bold text-white">
                NF
              </div>
            </div>
            <p className="text-xl font-semibold tracking-tight text-neutral-900">No assistant connected</p>
            <p className="mt-2 max-w-sm text-sm text-neutral-500">
              Publish an assistant in your NovaFlow workspace, then refresh.
            </p>
            <button
              type="button"
              onClick={loadApps}
              className="mt-6 rounded-xl bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white shadow-lg transition-transform hover:scale-[1.02] hover:bg-neutral-800"
            >
              Refresh
            </button>
          </div>
        ) : (
          <>
            <ChatMessages
              messages={messages}
              streaming={streaming}
              error={error}
              assistantName={selectedApp?.name}
              onSuggest={sendMessage}
            />
            <ChatInput
              onSend={sendMessage}
              onStop={stop}
              disabled={!selectedApp || streaming}
              streaming={streaming}
            />
            </>
          )}
      </div>
    </div>
  );
}
