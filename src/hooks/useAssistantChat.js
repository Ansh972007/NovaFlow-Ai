"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AssistantChatSocket } from "@/lib/chat/websocket";
import { saveSessionMessages, upsertSession } from "@/lib/chat/storage";
import { generateId } from "@/lib/utils";
import { createConversation } from "@/lib/api/conversations";

function isEmptyAssistant(m) {
  if (!m || m.role !== "assistant") return false;
  const hasContent = Boolean(String(m.content || "").trim());
  const hasEvent = Boolean(m.event);
  return !hasContent && !hasEvent && !m.streaming;
}

function pruneEmptyAssistants(list) {
  return (list || []).filter((m) => !isEmptyAssistant(m));
}

export function useAssistantChat({ app, sessionId, initialMessages = [] }) {
  const [messages, setMessages] = useState(() => pruneEmptyAssistants(initialMessages));
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [connectionStatus, setConnectionStatus] = useState("connected");
  const [planningLabel, setPlanningLabel] = useState("");
  const socketRef = useRef(null);
  const botMsgIdRef = useRef(null);
  const conversationIdRef = useRef("");
  const guideShownRef = useRef(false);
  const pendingAiosEventsRef = useRef([]);
  const aiosTurnActiveRef = useRef(false);

  const persist = useCallback(
    (nextMessages, title) => {
      if (!sessionId || !app) return;
      const cleaned = pruneEmptyAssistants(nextMessages);
      saveSessionMessages(sessionId, cleaned, title);
      upsertSession({
        id: sessionId,
        appId: app.id,
        appName: app.name,
        flowType: app.flow_type,
        title: title || cleaned.find((m) => m.role === "user")?.content,
      });
    },
    [sessionId, app]
  );

  const ensureConversation = useCallback(async () => {
    if (!app?.id || !sessionId) return conversationIdRef.current || "";
    if (conversationIdRef.current) return conversationIdRef.current;

    const key = `nf_conv_${app.id}_${sessionId}`;
    try {
      const existing = localStorage.getItem(key);
      if (existing) {
        conversationIdRef.current = existing;
        return existing;
      }
    } catch {
      /* ignore */
    }

    try {
      const created = await createConversation({
        title: `Chat ${app.name || "session"}`,
        assistantId: app.id === "default_assistant" ? "" : app.id,
        conversationType: "assistant",
      });
      const createdId = created?.id || "";
      conversationIdRef.current = createdId;
      if (createdId) localStorage.setItem(key, createdId);
      return createdId;
    } catch {
      return conversationIdRef.current || "";
    }
  }, [app, sessionId]);

  const connect = useCallback(async () => {
    if (!app || !sessionId) return;
    
    // Pre-flight authentication check
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("nf_token");
      if (!token) {
        setError("Authentication required. Please log in again.");
        const path = window.location.pathname;
        if (!path.startsWith("/login") && !path.startsWith("/setup")) {
          window.location.assign(`/login?next=${encodeURIComponent(path)}`);
        }
        return;
      }
    }
    
    socketRef.current?.disconnect();

    const socket = new AssistantChatSocket({
      app,
      chatId: sessionId,
      handlers: {
        onGuide: (text) => {
          // Once per session — never spam full bubbles with assistant description
          if (guideShownRef.current) return;
          const t = String(text || "").trim();
          if (!t) return;
          guideShownRef.current = true;
          // Soft subtitle only if chat is completely empty
          setMessages((prev) => {
            if (prev.length > 0) return prev;
            if (prev.some((m) => m.role === "user" || m.event || m.isGuide)) return prev;
            return [
              {
                id: generateId(),
                role: "assistant",
                content: t,
                streaming: false,
                isGuide: true,
              },
            ];
          });
        },
        onStart: () => {
          if (aiosTurnActiveRef.current) return;
          pendingAiosEventsRef.current = [];
          const id = generateId();
          botMsgIdRef.current = id;
          setMessages((prev) => [
            ...prev,
            { id, role: "assistant", content: "", streaming: true },
          ]);
        },
        onStream: (chunk, _data, reasoning) => {
          setMessages((prev) => {
            let id = botMsgIdRef.current;
            if (!id) {
              id = generateId();
              botMsgIdRef.current = id;
              return [
                ...prev,
                {
                  id,
                  role: "assistant",
                  content: chunk || "",
                  reasoning: reasoning || "",
                  streaming: true,
                },
              ];
            }
            return prev.map((m) =>
              m.id === id
                ? {
                    ...m,
                    content: (m.content || "") + (chunk || ""),
                    reasoning: (m.reasoning || "") + (reasoning || ""),
                    streaming: true,
                  }
                : m
            );
          });
        },
        onStreamEnd: (chunk, data) => {
          const receipt = data?.receipt || null;
          if (receipt?.planning_label) {
            setPlanningLabel(receipt.planning_label);
          }
          const endText = String(chunk || "").trim();
          const buffered = pendingAiosEventsRef.current || [];
          const primary = buffered[0] || null;
          const aiosOnlyEnd = Boolean(data?.aios_only);
          const aiosOnly = Boolean(aiosOnlyEnd || aiosTurnActiveRef.current || primary);
          pendingAiosEventsRef.current = [];
          aiosTurnActiveRef.current = false;

          const resolveContent = (existing) => {
            const trimmed = String(existing || "").trim();
            if (trimmed) return trimmed;
            if (endText) return endText;
            if (primary?.data?.message) return String(primary.data.message);
            if (primary?.data?.goal) return String(primary.data.goal);
            if (aiosOnly) return "";
            return "";
          };

          const attachAios = buffered.length > 0 || aiosOnlyEnd;

          setMessages((prev) => {
            const streamingId = botMsgIdRef.current;

            if (!streamingId) {
              const content = resolveContent("");
              return [
                ...prev,
                {
                  id: generateId(),
                  role: "assistant",
                  content,
                  streaming: false,
                  event: attachAios ? primary || undefined : undefined,
                  aiosEvents: attachAios && buffered.length ? buffered : undefined,
                  receipt,
                },
              ];
            }

            return prev.map((m) => {
              if (m.id !== streamingId) return m;
              return {
                ...m,
                content: resolveContent(m.content),
                streaming: false,
                event: attachAios ? primary || m.event : undefined,
                aiosEvents: attachAios
                  ? buffered.length
                    ? buffered
                    : m.aiosEvents
                  : undefined,
                receipt: receipt || m.receipt,
              };
            });
          });
          botMsgIdRef.current = null;
          setStreaming(false);
        },
        onDone: () => {
          setStreaming(false);
          botMsgIdRef.current = null;
          pendingAiosEventsRef.current = [];
          aiosTurnActiveRef.current = false;
          setMessages((prev) =>
            prev.map((m) => ({ ...m, streaming: false }))
          );
        },
        onError: (msg) => {
          setStreaming(false);
          const streamingId = botMsgIdRef.current;
          botMsgIdRef.current = null;
          pendingAiosEventsRef.current = [];
          aiosTurnActiveRef.current = false;
          
          const errText = msg || "API key or provider configuration notice. Please set your API key in Settings -> API Keys.";
          setError(errText);
          
          setMessages((prev) => {
            const filtered = prev.filter((m) => m.id !== streamingId);
            return [
              ...filtered,
              {
                id: generateId(),
                role: "assistant",
                content: errText,
                streaming: false,
              },
            ];
          });
        },
        onDisconnect: () => {
          setStreaming(false);
          setConnectionStatus("reconnecting");
        },
        onConversation: (conversationId) => {
          conversationIdRef.current = conversationId || "";
        },
        onAiosEvent: (event) => {
          aiosTurnActiveRef.current = true;
          if (event) {
            pendingAiosEventsRef.current = [...(pendingAiosEventsRef.current || []), event];
          }
          setStreaming(false);
          const streamingId = botMsgIdRef.current;
          if (streamingId) {
            setMessages((prev) =>
              prev.filter((m) => !(m.id === streamingId && !String(m.content || "").trim()))
            );
            botMsgIdRef.current = null;
          }
        },
      },
    });

    socketRef.current = socket;
    await socket.connect();
    setConnectionStatus("connected");
  }, [app, sessionId]);

  const lastSessionIdRef = useRef(sessionId);

  useEffect(() => {
    if (lastSessionIdRef.current !== sessionId) {
      lastSessionIdRef.current = sessionId;
      setMessages(pruneEmptyAssistants(initialMessages));
      setError("");
      setStreaming(false);
      botMsgIdRef.current = null;
      conversationIdRef.current = "";
      guideShownRef.current = false;
      pendingAiosEventsRef.current = [];
      aiosTurnActiveRef.current = false;
    }
  }, [sessionId, initialMessages]);

  useEffect(() => {
    if (!app || !sessionId) return;
    connect().catch((err) => setError(err.message));
    return () => socketRef.current?.disconnect();
  }, [app?.id, sessionId, connect]);

  useEffect(() => {
    if (messages.length) persist(messages);
  }, [messages, persist]);

  const sendMessage = useCallback(
    async (text, options = {}) => {
      const trimmed = text ? String(text).trim() : "";
      const effectiveApp = app || { id: "default_assistant", name: "NovaFlow AI", flow_type: "assistant" };
      if (!trimmed || streaming) return;

      setError("");
      setStreaming(true);

      const historyForModel = messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .filter((m) => String(m.content || "").trim())
        .map((m) => ({ role: m.role, content: m.content }))
        .slice(-12);

      const userMsg = {
        id: generateId(),
        role: "user",
        content: trimmed,
        streaming: false,
        attachments: options.attachments || [],
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const ensuredConversationId = await ensureConversation();
        if (
          !socketRef.current?.connected ||
          socketRef.current?.ws?.readyState !== WebSocket.OPEN
        ) {
          await connect();
        }
        await socketRef.current.sendMessage(trimmed, historyForModel, {
          conversationId: ensuredConversationId || conversationIdRef.current || "",
          attachmentIds: options.attachmentIds || [],
        });
      } catch (err) {
        const errMsg = err.message || "Failed to send message";
        setError(errMsg);
        setStreaming(false);
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: "assistant",
            content: `Notice: ${errMsg}`,
            streaming: false,
          },
        ]);
      }
    },
    [app, streaming, connect, messages, ensureConversation]
  );

  const stop = useCallback(() => {
    socketRef.current?.stop();
    setStreaming(false);
  }, []);

  const regenerate = useCallback(async () => {
    if (streaming || !app) return;

    let lastUser = "";
    let historyForModel = [];

    setMessages((prev) => {
      const copy = [...prev];
      while (copy.length && copy[copy.length - 1].role === "assistant") {
        copy.pop();
      }
      const uIdx = [...copy].map((m) => m.role).lastIndexOf("user");
      if (uIdx < 0) return prev;
      lastUser = copy[uIdx].content || "";
      historyForModel = copy
        .slice(0, uIdx)
        .filter((m) => m.role === "user" || m.role === "assistant")
        .filter((m) => String(m.content || "").trim())
        .map((m) => ({ role: m.role, content: m.content }))
        .slice(-12);
      return copy.slice(0, uIdx);
    });

    setError("");
    await new Promise((r) => setTimeout(r, 0));
    const trimmed = (lastUser || "").trim();
    if (!trimmed) return;

    setStreaming(true);
    setMessages((prev) => [
      ...prev,
      { id: generateId(), role: "user", content: trimmed, streaming: false },
    ]);

    try {
      if (
        !socketRef.current?.connected ||
        socketRef.current?.ws?.readyState !== WebSocket.OPEN
      ) {
        await connect();
      }
      socketRef.current.sendMessage(trimmed, historyForModel, {
        conversationId: conversationIdRef.current || (await ensureConversation()) || "",
      });
    } catch (err) {
      setError(err.message || "Failed to regenerate");
      setStreaming(false);
    }
  }, [app, streaming, connect, ensureConversation]);

  return {
    messages,
    streaming,
    error,
    connectionStatus,
    planningLabel,
    sendMessage,
    stop,
    regenerate,
    setError,
    conversationIdRef,
    ensureConversation,
  };
}
