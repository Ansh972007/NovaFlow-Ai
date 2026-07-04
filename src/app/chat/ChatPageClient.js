"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import Logo from "@/components/Logo";
import LiveBackground from "@/components/LiveBackground";
import ChatSidebar from "@/components/chat/ChatSidebar";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";
import { useAssistantChat } from "@/hooks/useAssistantChat";
import { getOnlineApps, getAssistants, FLOW_TYPE } from "@/lib/api/apps";
import { getUserInfo } from "@/lib/api/auth";
import {
  getSessionsForApp,
  getSessionMessages,
  upsertSession,
} from "@/lib/chat/storage";
import { generateId } from "@/lib/utils";

function ChatLoading() {
  return (
    <div className="relative flex min-h-screen items-center justify-center">
      <LiveBackground variant="subtle" showNetwork />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative z-10 flex flex-col items-center gap-4"
      >
        <motion.span
          animate={{ scale: [1, 1.08, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="flex h-14 w-14 items-center justify-center rounded-full bg-black text-lg font-bold text-white"
        >
          NF
        </motion.span>
        <p className="text-sm text-muted">Loading your workspace…</p>
      </motion.div>
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
      .catch(() => {
        router.push("/login");
      })
      .finally(() => setAuthChecked(true));
  }, [router]);

  useEffect(() => {
    if (!authChecked || !user) return;
    loadApps().then((list) => {
      if (!list.length) return;
      const app =
        list.find((a) => String(a.id) === String(appIdParam)) || list[0];
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

  const headerTitle = useMemo(
    () => selectedApp?.name || "Chat",
    [selectedApp]
  );

  if (!authChecked) {
    return <ChatLoading />;
  }

  return (
    <div className="relative flex h-screen flex-col overflow-hidden">
      <LiveBackground variant="subtle" showNetwork={false} showOrbs />

      <header className="relative z-20 flex h-14 shrink-0 items-center justify-between border-b border-border/80 bg-white/80 px-4 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <Logo size="sm" />
          <span className="hidden text-muted sm:inline">/</span>
          <span className="hidden max-w-[200px] truncate text-sm font-medium sm:inline">
            {headerTitle}
          </span>
          {streaming && (
            <span className="flex items-center gap-1.5 rounded-full bg-black px-2.5 py-0.5 text-[10px] font-medium text-white">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
              Live
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link href="/" className="rounded-full px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface hover:text-foreground">
            Home
          </Link>
          <Link href="/dashboard" className="rounded-full px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface hover:text-foreground">
            Dashboard
          </Link>
          {user && (
            <span className="hidden rounded-full border border-border px-3 py-1 text-xs text-muted md:inline">
              {user.user_name}
            </span>
          )}
        </div>
      </header>

      <div className="relative z-10 flex min-h-0 flex-1 flex-col md:flex-row">
        <ChatSidebar
          apps={apps}
          sessions={sessions}
          selectedAppId={selectedApp?.id}
          selectedSessionId={sessionId}
          onSelectApp={handleSelectApp}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          loading={loadingApps}
        />

        <div className="flex min-h-0 flex-1 flex-col bg-white/60 backdrop-blur-sm">
          <ChatMessages messages={messages} streaming={streaming} error={error} />
          <ChatInput
            onSend={sendMessage}
            onStop={stop}
            disabled={!selectedApp || streaming}
            streaming={streaming}
          />
        </div>
      </div>
    </div>
  );
}
