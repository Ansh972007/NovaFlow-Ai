"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

const suggestions = [
  "Summarize my documents",
  "Write a short email",
  "Explain step by step",
  "What can you do?",
];

const messageVariants = {
  hidden: { opacity: 0, y: 12, scale: 0.98 },
  visible: { opacity: 1, y: 0, scale: 1 },
};

export default function ChatMessages({ messages, streaming, error, assistantName, onSuggest }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, streaming, error]);

  const showThinking =
    streaming && messages.length > 0 && messages[messages.length - 1]?.role === "user";

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-8 sm:px-6">
        {messages.length === 0 && !error ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-1 flex-col items-center justify-center py-12 text-center"
            >
              <div className="relative mb-6 flex h-20 w-20 items-center justify-center">
                <div className="chat-empty-ring-outer absolute inset-0 rounded-2xl" />
                <div className="chat-empty-ring absolute inset-1 rounded-2xl" />
                <motion.div
                  animate={{ scale: [1, 1.05, 1], rotate: [0, 2, -2, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                  className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-neutral-900 text-sm font-bold text-white shadow-xl"
                >
                  NF
                </motion.div>
              </div>

              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.15 }}
                className="text-2xl font-semibold tracking-tight text-neutral-900"
              >
                {assistantName || "NovaFlow Assistant"}
              </motion.h2>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.25 }}
                className="mt-2 max-w-sm text-sm text-neutral-500"
              >
                Blueprint-ready AI workspace. Ask anything or pick a starter below.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="mt-10 flex w-full max-w-lg flex-wrap justify-center gap-2.5"
              >
                {suggestions.map((text, i) => (
                  <motion.button
                    key={text}
                    type="button"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 + i * 0.06 }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onSuggest?.(text)}
                    className="chat-suggest-chip rounded-full px-4 py-2.5 text-xs font-medium text-neutral-700"
                  >
                    {text}
                  </motion.button>
                ))}
              </motion.div>
            </motion.div>
          ) : null}

        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              variants={messageVariants}
              initial="hidden"
              animate="visible"
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-900 text-[9px] font-bold text-white shadow-md">
                  NF
                </div>
              )}

              <div className={`max-w-[85%] sm:max-w-[78%] ${msg.role === "user" ? "text-right" : ""}`}>
                {msg.role === "assistant" && (
                  <p className="mb-1.5 text-[11px] font-medium tracking-wide text-neutral-400 uppercase">
                    {assistantName || "Assistant"}
                  </p>
                )}
                <div
                  className={`inline-block px-4 py-3 text-sm leading-relaxed sm:text-[15px] ${
                    msg.role === "user"
                      ? "chat-bubble-user text-left"
                      : `chat-bubble-assistant text-neutral-800${msg.streaming ? " chat-bubble-streaming" : ""}`
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">
                    {msg.content || (msg.streaming ? "" : "…")}
                  </p>
                  {msg.streaming && !msg.content && (
                    <span className="inline-flex gap-1 py-1">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
                          style={{ animationDelay: `${i * 120}ms` }}
                        />
                      ))}
                    </span>
                  )}
                  {msg.streaming && msg.content && (
                    <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-neutral-400 align-middle" />
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {showThinking && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex gap-3"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-neutral-200 bg-white text-[9px] font-bold text-neutral-500">
                NF
              </div>
              <div className="chat-bubble-assistant flex items-center gap-2 px-4 py-3 text-sm text-neutral-500">
                <span className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
                      style={{ animationDelay: `${i * 140}ms` }}
                    />
                  ))}
                </span>
                Composing…
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-700 backdrop-blur-sm"
          >
            {error}
          </motion.div>
        )}

        <div ref={bottomRef} className="h-px shrink-0" />
      </div>
    </div>
  );
}
