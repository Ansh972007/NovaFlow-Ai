"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import ChatSidebar from "@/components/chat/ChatSidebar";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";
import { useAssistantChat } from "@/hooks/useAssistantChat";
import { getOnlineApps, getAssistants, getAssistantInfo, FLOW_TYPE } from "@/lib/api/apps";
import { getUserInfo } from "@/lib/api/auth";
import {
  getSessionsForApp,
  getSessionMessages,
  upsertSession,
} from "@/lib/chat/storage";
import { generateId } from "@/lib/utils";

function ChatLoading() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10 flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative flex h-12 w-12 items-center justify-center">
            <div className="chat-empty-ring absolute inset-0 rounded-xl" />
            <div className="h-10 w-10 animate-pulse rounded-lg bg-neutral-900/90" />
          </div>
          <p className="text-sm text-neutral-500">Loading workspace…</p>
        </div>
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

  const chatKey = `${selectedApp?.id || "none"}-${sessionId || "none"}`;

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
    if (!selectedApp?.id) return;

    const appSessions = getSessionsForApp(selectedApp.id);
    setSessions(appSessions);

    if (sessionParam && appSessions.some((s) => s.id === sessionParam)) {
      setSessionId(sessionParam);
      setInitialMessages(getSessionMessages(sessionParam));
      return;
    }

    if (appSessions.length > 0) {
      const first = appSessions[0];
      setSessionId(first.id);
      setInitialMessages(getSessionMessages(first.id));
      router.replace(`/chat?app=${selectedApp.id}&session=${first.id}`);
      return;
    }

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
  }, [selectedApp?.id, sessionParam, router]);

  const startNewChat = useCallback(
    (app = selectedApp) => {
      if (!app?.id) return null;
      const newId = generateId();
      upsertSession({
        id: newId,
        appId: app.id,
        appName: app.name,
        flowType: app.flow_type,
        title: "New chat",
        messages: [],
      });
      const nextSessions = getSessionsForApp(app.id);
      setSessions(nextSessions);
      setSelectedApp(app);
      setSessionId(newId);
      setInitialMessages([]);
      router.push(`/chat?app=${app.id}&session=${newId}`);
      return newId;
    },
    [selectedApp, router]
  );

  const handleSelectApp = (app) => {
    startNewChat(app);
  };

  const handleSelectSession = (session) => {
    setSessionId(session.id);
    setInitialMessages(getSessionMessages(session.id));
    router.push(`/chat?app=${session.appId}&session=${session.id}`);
  };

  const handleNewChat = () => {
    if (apps.length && !selectedApp) {
      startNewChat(apps[0]);
      return;
    }
    startNewChat();
  };

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
    <div className="chat-shell relative flex h-[100dvh] flex-col overflow-hidden">
      <WorkspaceLiveBackground active={streaming} />

      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        <AppHeader user={user} />

        <div className="flex min-h-0 flex-1">
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
          />

          <div className="chat-main-panel relative flex min-h-0 min-w-0 flex-1 flex-col">
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className="flex shrink-0 items-center justify-between gap-3 border-b border-neutral-200/70 bg-white/75 px-3 py-3 backdrop-blur-xl sm:px-5"
            >
              <div className="flex min-w-0 items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setSidebarOpen(true)}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-neutral-200/80 bg-white text-neutral-600 shadow-sm transition-colors hover:bg-neutral-50 lg:hidden"
                  aria-label="Open chat sidebar"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="truncate text-sm font-semibold tracking-tight text-neutral-900 sm:text-base">
                      {headerTitle}
                    </h1>
                    {ragCount > 0 && (
                      <Link
                        href={selectedApp ? `/apps/${selectedApp.id}` : "/apps"}
                        className="workspace-badge-live shrink-0"
                        title="Knowledge bases linked for RAG"
                      >
                        RAG · {ragCount}
                      </Link>
                    )}
                    {streaming && (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200/80 bg-emerald-50/90 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                        <span className="chat-status-dot h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        Live
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate text-xs text-neutral-500">
                    {messages.length ? `${messages.length} messages` : "Start a new conversation"}
                  </p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleNewChat}
                  disabled={loadingApps || !apps.length}
                  className="hidden rounded-full border border-neutral-200 bg-white px-3.5 py-2 text-xs font-semibold text-neutral-800 shadow-sm transition-colors hover:bg-neutral-50 disabled:opacity-40 sm:inline-flex"
                >
                  + New chat
                </button>
                {messages.length > 0 && (
                  <button
                    type="button"
                    onClick={exportTranscript}
                    className="rounded-full border border-neutral-200 bg-white px-3.5 py-2 text-xs font-medium text-neutral-600 shadow-sm transition-colors hover:bg-neutral-50 hover:text-neutral-900"
                  >
                    Export
                  </button>
                )}
                {selectedApp && (
                  <Link
                    href={`/apps/${selectedApp.id}`}
                    className="rounded-full border border-neutral-200 bg-white px-3.5 py-2 text-xs font-medium text-neutral-600 shadow-sm transition-colors hover:bg-neutral-50 hover:text-neutral-900"
                  >
                    Configure
                  </Link>
                )}
              </div>
            </motion.div>

            {!selectedApp && !loadingApps ? (
              <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
                <div className="workspace-panel max-w-md rounded-[1.5rem] p-8">
                  <div className="relative mx-auto mb-5 flex h-14 w-14 items-center justify-center">
                    <div className="chat-empty-ring absolute inset-0 rounded-xl" />
                    <div className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-900 text-sm font-bold text-white">
                      NF
                    </div>
                  </div>
                  <p className="text-xl font-semibold tracking-tight text-neutral-900">No assistant connected</p>
                  <p className="mt-2 text-sm leading-relaxed text-neutral-500">
                    Publish an assistant in Apps, then return here to chat.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    <Link href="/apps" className="btn-primary !py-2.5 !text-sm">
                      Go to Apps
                    </Link>
                    <button
                      type="button"
                      onClick={loadApps}
                      className="rounded-full border border-neutral-200 bg-white px-5 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
                    >
                      Refresh
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div key={chatKey} className="flex min-h-0 flex-1 flex-col">
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
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
