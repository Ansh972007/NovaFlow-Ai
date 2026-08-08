"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import ChatSidebar from "@/components/chat/ChatSidebar";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";
import ChatPlanningSelector from "@/components/chat/ChatPlanningSelector";
import { useAssistantChat } from "@/hooks/useAssistantChat";
import { getOnlineApps, getAssistants, getAssistantInfo, FLOW_TYPE } from "@/lib/api/apps";
import { getUserInfo } from "@/lib/api/auth";
import {
  deleteSession,
  getSessionsForApp,
  getSessionMessages,
  upsertSession,
} from "@/lib/chat/storage";
import { generateId } from "@/lib/utils";

function ChatLoading() {
  return <WorkspaceLoading message="Loading chat…" />;
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

  const { messages, streaming, error, connectionStatus, planningLabel, sendMessage, stop, regenerate, setError, ensureConversation } =
    useAssistantChat({
    app: selectedApp,
    sessionId,
    initialMessages,
    });

  const composerPending = useMemo(
    () =>
      messages.some((m) => {
        const t = m?.event?.type || "";
        if (!t.startsWith("aios_")) return false;
        if (t === "aios_deploy" && m?.event?.data?.workflow_id) return false;
        if (t === "aios_cancelled") return false;
        return true;
      }) &&
      !messages.some((m) => m?.event?.type === "aios_deploy" && m?.event?.data?.workflow_id),
    [messages],
  );

  const handleVoiceCommand = useCallback(
    (cmd) => {
      if (!cmd?.action) return false;
      if (cmd.action === "navigate" && cmd.path) {
        router.push(cmd.path);
        return true;
      }
      if (cmd.action === "suggest" && cmd.phrase) {
        sendMessage(cmd.phrase);
        return true;
      }
      return false;
    },
    [router, sendMessage],
  );

  const loadApps = useCallback(async () => {
    setLoadingApps(true);
    let retryCount = 0;
    const maxRetries = 3;
    
    const attemptLoad = async () => {
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
      } catch (error) {
        console.error("Error loading apps:", error);
        if (retryCount < maxRetries) {
          retryCount++;
          const delay = Math.min(1000 * Math.pow(2, retryCount), 5000);
          console.log(`Retrying app load in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          return attemptLoad();
        }
        setApps([]);
        return [];
      }
    };
    
    const result = await attemptLoad();
    setLoadingApps(false);
    return result;
  }, []);

  useEffect(() => {
    let retryCount = 0;
    const maxRetries = 3;
    
    const attemptGetUserInfo = async () => {
      try {
        const userInfo = await getUserInfo();
        setUser(userInfo);
        setAuthChecked(true);
      } catch (error) {
        console.error("Error getting user info:", error);
        if (retryCount < maxRetries) {
          retryCount++;
          const delay = Math.min(1000 * Math.pow(2, retryCount), 5000);
          console.log(`Retrying user info in ${delay}ms...`);
          setTimeout(attemptGetUserInfo, delay);
        } else {
          router.push("/login");
          setAuthChecked(true);
        }
      }
    };
    
    attemptGetUserInfo();
  }, [router]);

  useEffect(() => {
    if (!authChecked || !user) return;
    loadApps().then((list) => {
      const defaultApp = { id: "default_assistant", name: "NovaFlow AI", flow_type: "assistant" };
      if (!list || !list.length) {
        setSelectedApp(defaultApp);
        setApps([defaultApp]);
        return;
      }
      const app = list.find((a) => String(a.id) === String(appIdParam)) || list[0];
      setSelectedApp(app || defaultApp);
    });
  }, [authChecked, user, loadApps, appIdParam]);

  useEffect(() => {
    if (!selectedApp?.id) {
      setRagCount(0);
      return;
    }
    const ft = String(selectedApp.flow_type || "").toLowerCase();
    if (ft === "workflow" || ft === "flow" || selectedApp.id === "default_assistant") {
      setRagCount(0);
      return;
    }
    getAssistantInfo(selectedApp.id)
      .then((info) => {
        const ids = info?.knowledge_ids || info?.knowledge_list?.map((k) => k.id) || [];
        setRagCount(ids.length);
      })
      .catch(() => setRagCount(0));
  }, [selectedApp?.id, selectedApp?.flow_type]);

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
      if (typeof window !== "undefined") {
        window.history.replaceState(null, "", `/chat?app=${selectedApp.id}&session=${first.id}`);
      }
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
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `/chat?app=${selectedApp.id}&session=${newId}`);
    }
  }, [selectedApp?.id]);

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

  const handleDeleteSession = useCallback(
    (targetId) => {
      const idToDelete = targetId || sessionId;
      if (!idToDelete) return;
      const remaining = deleteSession(idToDelete);
      if (selectedApp?.id) {
        const appSessions = remaining.filter((s) => s.appId === selectedApp.id);
        setSessions(appSessions);
        if (idToDelete === sessionId) {
          if (appSessions.length > 0) {
            const first = appSessions[0];
            setSessionId(first.id);
            setInitialMessages(getSessionMessages(first.id));
            if (typeof window !== "undefined") {
              window.history.replaceState(null, "", `/chat?app=${selectedApp.id}&session=${first.id}`);
            }
          } else {
            startNewChat(selectedApp);
          }
        }
      }
    },
    [sessionId, selectedApp, startNewChat]
  );

  const headerTitle = useMemo(() => selectedApp?.name || "Build", [selectedApp]);
  const hasAiosSession = useMemo(
    () => messages.some((m) => m?.event?.type?.startsWith?.("aios_")),
    [messages]
  );

  function exportTranscript() {
    if (!messages?.length) return;
    const lines = messages.map((m) => {
      const role = m.role === "user" ? "You" : "Assistant";
      const parts = [String(m.content || "").trim()];
      const events = m.aiosEvents?.length ? m.aiosEvents : m.event ? [m.event] : [];
      for (const ev of events) {
        if (!ev?.type) continue;
        const d = ev.data || {};
        const summary = d.message || d.title || ev.type;
        parts.push(`[${ev.type}] ${summary}`);
      }
      if (m.receipt?.rag_hits?.length) {
        parts.push(`[RAG] ${m.receipt.rag_hits.length} citation(s)`);
      }
      return `**${role}:** ${parts.filter(Boolean).join("\n")}`;
    });
    const md = `# ${headerTitle}\n\n${lines.join("\n\n")}\n`;
    const blob = new Blob([md], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `novaflow-build-${sessionId || "session"}.md`;
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
            onDeleteSession={handleDeleteSession}
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
                    {hasAiosSession && (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200/80 bg-indigo-50/90 px-2.5 py-0.5 text-[10px] font-semibold text-indigo-700">
                        AIOS
                      </span>
                    )}
                    {ragCount > 0 && (
                      <Link
                        href={selectedApp ? `/projects/assistants/${selectedApp.id}` : "/projects?tab=assistants"}
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
                    <ChatPlanningSelector
                      label={planningLabel || "Planning model"}
                      onSelectModel={(phrase) => sendMessage(phrase)}
                    />
                  </div>
                  <p className="mt-0.5 truncate text-xs text-neutral-500">
                    {messages.length ? `${messages.length} messages` : "Start a new build session"}
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
                  + New build
                </button>
                {sessionId && (
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm("Are you sure you want to delete this chat session?")) {
                        handleDeleteSession();
                      }
                    }}
                    className="rounded-full border border-red-200 bg-red-50/80 px-3.5 py-2 text-xs font-semibold text-red-700 shadow-sm transition-colors hover:bg-red-100/80"
                    title="Delete current chat"
                  >
                    Delete chat
                  </button>
                )}
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
                    href={`/projects/assistants/${selectedApp.id}`}
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
                  <p className="text-xl font-semibold tracking-tight text-neutral-900">No composer interface connected</p>
                  <p className="mt-2 text-sm leading-relaxed text-neutral-500">
                    Publish an assistant in Projects, then return here to build.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    <Link href="/projects?tab=assistants" className="btn-primary !py-2.5 !text-sm">
                      Go to Projects
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
              <div className="flex min-h-0 flex-1 flex-col">
                {connectionStatus === "reconnecting" && (
                  <p className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
                    Reconnecting to chat…
                  </p>
                )}
                <ChatMessages
                  messages={messages}
                  streaming={streaming}
                  error={error}
                  assistantName={selectedApp?.name}
                  onSuggest={sendMessage}
                  onRegenerate={regenerate}
                  onClearError={() => setError("")}
                  hasKnowledge={Boolean(selectedApp?.knowledge_list?.length || selectedApp?.knowledge_ids?.length)}
                />
                <ChatInput
                  onSend={sendMessage}
                  onStop={stop}
                  disabled={!selectedApp || streaming}
                  streaming={streaming}
                  ensureConversation={ensureConversation}
                  composerPending={composerPending}
                  onVoiceCommand={handleVoiceCommand}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
