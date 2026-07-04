"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ChatSidebar from "@/components/chat/ChatSidebar";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";
import ChatLiveBackground from "@/components/chat/ChatLiveBackground";
import { useAssistantChat } from "@/hooks/useAssistantChat";
import { getOnlineApps, getAssistants, FLOW_TYPE } from "@/lib/api/apps";
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
      <ChatLiveBackground />
      <div className="relative z-10 flex flex-col items-center gap-4">
        <div className="h-10 w-10 animate-pulse rounded-lg bg-neutral-200/80" />
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

  if (!authChecked) {
    return <ChatLoading />;
  }

  return (
    <div className="chat-shell relative flex h-[100dvh] overflow-hidden">
      <ChatLiveBackground className="fixed inset-0 z-0" active={streaming} />

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

      <div className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="relative flex min-h-0 flex-1 flex-col bg-white/85 backdrop-blur-sm">
        <header className="flex h-12 shrink-0 items-center justify-between border-b border-neutral-200/80 bg-white/90 px-3 backdrop-blur-md sm:px-4">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="flex h-8 w-8 items-center justify-center rounded-md text-neutral-500 hover:bg-neutral-100 md:hidden"
              aria-label="Open menu"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-neutral-900">{headerTitle}</p>
              {streaming && (
                <p className="flex items-center gap-1 text-[10px] text-neutral-500">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  Responding…
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1">
            <Link
              href="/dashboard"
              className="hidden rounded-md px-2.5 py-1.5 text-xs text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 sm:inline"
            >
              Dashboard
            </Link>
            <Link
              href="/knowledge"
              className="hidden rounded-md px-2.5 py-1.5 text-xs text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 sm:inline"
            >
              Knowledge
            </Link>
            <Link
              href="/"
              className="rounded-md px-2.5 py-1.5 text-xs text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
            >
              Home
            </Link>
          </div>
        </header>

        {!selectedApp && !loadingApps ? (
          <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-100 text-sm font-bold text-neutral-600">
              NF
            </div>
            <p className="text-lg font-semibold text-neutral-900">No assistant connected</p>
            <p className="mt-2 max-w-sm text-sm text-neutral-500">
              Publish an assistant in your NovaFlow workspace, then refresh.
            </p>
            <button
              type="button"
              onClick={loadApps}
              className="mt-5 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
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
    </div>
  );
}
