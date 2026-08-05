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

    const created = await createConversation({
      title: `Chat ${app.name || "session"}`,
      assistantId: app.id,
      conversationType: "assistant",
    });
    const createdId = created?.id || "";
    conversationIdRef.current = createdId;
    try {
      if (createdId) localStorage.setItem(key, createdId);
    } catch {
      /* ignore */
    }
    return createdId;
  }, [app, sessionId]);

  const connect = useCallback(async () => {
    if (!app || !sessionId) return;
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
          pendingAiosEventsRef.current = [];
          aiosTurnActiveRef.current = false;
          const id = generateId();
          botMsgIdRef.current = id;
          setMessages((prev) => [
            ...prev,
            { id, role: "assistant", content: "", streaming: true },
          ]);
        },
        onStream: (chunk, _data, reasoning) => {
          setMessages((prev) => {
            const id = botMsgIdRef.current;
            if (!id) return prev;
            return prev.map((m) =>
              m.id === id
                ? {
                    ...m,
                    content: m.content + chunk,
                    reasoning: (m.reasoning || "") + (reasoning || ""),
                    streaming: true,
                  }
                : m
            );
          });
        },
        onStreamEnd: (chunk, data) => {
          const receipt = data?.receipt || null;
          const endText = String(chunk || "").trim();
          const isAios = receipt?.event_type === "aios" || aiosTurnActiveRef.current;
          const buffered = pendingAiosEventsRef.current || [];
          pendingAiosEventsRef.current = [];
          aiosTurnActiveRef.current = false;

          setMessages((prev) => {
            let next = [...prev];
            const streamingId = botMsgIdRef.current;
            // Drop empty streaming placeholder
            if (streamingId) {
              next = next.filter(
                (m) => !(m.id === streamingId && !String(m.content || "").trim() && !m.event)
              );
            }

            if (isAios || buffered.length) {
              const primary = buffered[0] || null;
              return pruneEmptyAssistants([
                ...next,
                {
                  id: generateId(),
                  role: "assistant",
                  content: endText || primary?.data?.message || "",
                  streaming: false,
                  event: primary || undefined,
                  receipt,
                },
              ]);
            }

            if (!streamingId) {
              if (!endText) return pruneEmptyAssistants(next);
              return [
                ...pruneEmptyAssistants(next),
                {
                  id: generateId(),
                  role: "assistant",
                  content: endText,
                  streaming: false,
                  receipt,
                },
              ];
            }
            next = next.map((m) => {
              if (m.id !== streamingId) return m;
              const content = `${m.content || ""}${chunk || ""}`.trim();
              if (!content) return { ...m, _drop: true, streaming: false };
              return {
                ...m,
                content,
                streaming: false,
                receipt,
              };
            });
            return pruneEmptyAssistants(next.filter((m) => !m._drop));
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
            pruneEmptyAssistants(prev.map((m) => ({ ...m, streaming: false })))
          );
        },
        onError: (msg) => {
          setError(msg);
          setStreaming(false);
          botMsgIdRef.current = null;
          pendingAiosEventsRef.current = [];
          aiosTurnActiveRef.current = false;
          setMessages((prev) => pruneEmptyAssistants(prev));
        },
        onDisconnect: () => {
          setStreaming(false);
        },
        onConversation: (conversationId) => {
          conversationIdRef.current = conversationId || "";
        },
        onAiosEvent: (event) => {
          // Buffer until end — one card per turn (wire already sends primary only)
          aiosTurnActiveRef.current = true;
          if (event && pendingAiosEventsRef.current.length === 0) {
            pendingAiosEventsRef.current = [event];
          }
          setStreaming(false);
          const streamingId = botMsgIdRef.current;
          if (streamingId) {
            setMessages((prev) =>
              prev.filter((m) => !(m.id === streamingId && !String(m.content || "").trim()))
            );
          }
        },
      },
    });

    socketRef.current = socket;
    await socket.connect();
  }, [app, sessionId]);

  useEffect(() => {
    setMessages(pruneEmptyAssistants(initialMessages));
    setError("");
    setStreaming(false);
    botMsgIdRef.current = null;
    conversationIdRef.current = "";
    guideShownRef.current = false;
    pendingAiosEventsRef.current = [];
    aiosTurnActiveRef.current = false;
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
      const trimmed = text.trim();
      if (!trimmed || streaming || !app) return;

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
        socketRef.current.sendMessage(trimmed, historyForModel, {
          conversationId: ensuredConversationId || conversationIdRef.current || "",
          attachmentIds: options.attachmentIds || [],
        });
      } catch (err) {
        setError(err.message || "Failed to send message");
        setStreaming(false);
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
    sendMessage,
    stop,
    regenerate,
    setError,
    conversationIdRef,
    ensureConversation,
  };
}
