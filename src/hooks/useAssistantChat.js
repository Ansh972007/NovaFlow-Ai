"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AssistantChatSocket } from "@/lib/chat/websocket";
import { saveSessionMessages, upsertSession } from "@/lib/chat/storage";
import { generateId } from "@/lib/utils";

export function useAssistantChat({ app, sessionId, initialMessages = [] }) {
  const [messages, setMessages] = useState(initialMessages);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const socketRef = useRef(null);
  const botMsgIdRef = useRef(null);

  const persist = useCallback(
    (nextMessages, title) => {
      if (!sessionId || !app) return;
      saveSessionMessages(sessionId, nextMessages, title);
      upsertSession({
        id: sessionId,
        appId: app.id,
        appName: app.name,
        flowType: app.flow_type,
        title: title || nextMessages.find((m) => m.role === "user")?.content,
      });
    },
    [sessionId, app]
  );

  const connect = useCallback(async () => {
    if (!app || !sessionId) return;
    socketRef.current?.disconnect();

    const socket = new AssistantChatSocket({
      app,
      chatId: sessionId,
      handlers: {
        onGuide: (text) => {
          setMessages((prev) => [
            ...prev,
            {
              id: generateId(),
              role: "assistant",
              content: text,
              streaming: false,
            },
          ]);
        },
        onStart: () => {
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
        onStreamEnd: (chunk) => {
          setMessages((prev) => {
            const id = botMsgIdRef.current;
            if (!id) return prev;
            return prev.map((m) =>
              m.id === id
                ? {
                    ...m,
                    content: m.content + (chunk || ""),
                    streaming: false,
                  }
                : m
            );
          });
          botMsgIdRef.current = null;
          setStreaming(false);
        },
        onDone: () => {
          setStreaming(false);
          botMsgIdRef.current = null;
          setMessages((prev) =>
            prev.map((m) => ({ ...m, streaming: false }))
          );
        },
        onError: (msg) => {
          setError(msg);
          setStreaming(false);
          botMsgIdRef.current = null;
        },
        onDisconnect: () => {
          setStreaming(false);
        },
      },
    });

    socketRef.current = socket;
    await socket.connect();
  }, [app, sessionId]);

  useEffect(() => {
    setMessages(initialMessages);
    setError("");
    setStreaming(false);
    botMsgIdRef.current = null;
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
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || streaming || !app) return;

      setError("");
      setStreaming(true);

      const userMsg = {
        id: generateId(),
        role: "user",
        content: trimmed,
        streaming: false,
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        if (
          !socketRef.current?.connected ||
          socketRef.current?.ws?.readyState !== WebSocket.OPEN
        ) {
          await connect();
        }
        socketRef.current.sendMessage(trimmed);
      } catch (err) {
        setError(err.message || "Failed to send message");
        setStreaming(false);
      }
    },
    [app, streaming, connect]
  );

  const stop = useCallback(() => {
    socketRef.current?.stop();
    setStreaming(false);
  }, []);

  return { messages, streaming, error, sendMessage, stop, setError };
}
