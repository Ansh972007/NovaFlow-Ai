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
  hidden: { opacity: 0, y: 10, scale: 0.98 },
  visible: { opacity: 1, y: 0, scale: 1 },
};

export default function ChatMessages({ messages, streaming, error, assistantName, onSuggest }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: streaming ? "auto" : "smooth",
      block: "end",
    });
  }, [messages.length, streaming, error]);

  const showThinking =
    streaming && messages.length > 0 && messages[messages.length - 1]?.role === "user";

  return (
    <div className="chat-messages-scroll flex flex-1 flex-col overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8">
        {messages.length === 0 && !error ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-1 flex-col items-center justify-center py-8 text-center"
          >
            <div className="workspace-panel w-full max-w-lg rounded-[1.5rem] p-8 sm:p-10">
              <div className="relative mx-auto mb-6 flex h-20 w-20 items-center justify-center">
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

              <h2 className="text-2xl font-semibold tracking-tight text-neutral-900">
                {assistantName || "NovaFlow Assistant"}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-neutral-500">
                Ask anything — your assistant is ready. Pick a starter or type below.
              </p>

              <div className="mt-8 flex flex-wrap justify-center gap-2.5">
                {suggestions.map((text, i) => (
                  <motion.button
                    key={text}
                    type="button"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.08 + i * 0.05 }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onSuggest?.(text)}
                    className="chat-suggest-chip rounded-full px-4 py-2.5 text-xs font-medium text-neutral-700"
                  >
                    {text}
                  </motion.button>
                ))}
              </div>
            </div>
          </motion.div>
        ) : null}

        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              variants={messageVariants}
              initial="hidden"
              animate="visible"
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-neutral-900 text-[10px] font-bold text-white shadow-md">
                  NF
                </div>
              )}

              <div className={`max-w-[88%] sm:max-w-[80%] ${msg.role === "user" ? "text-right" : ""}`}>
                {msg.role === "assistant" && (
                  <p className="mb-1.5 text-[10px] font-semibold tracking-[0.14em] text-neutral-400 uppercase">
                    {assistantName || "Assistant"}
                  </p>
                )}
                <div
                  className={`inline-block text-left text-sm leading-relaxed sm:text-[15px] ${
                    msg.role === "user"
                      ? "chat-bubble-user px-4 py-3"
                      : `chat-bubble-assistant px-4 py-3.5 text-neutral-800${msg.streaming ? " chat-bubble-streaming" : ""}`
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
                  {msg.role === "assistant" && msg.receipt && !msg.streaming && (
                    <details className="mt-3 border-t border-black/[0.06] pt-3 text-left">
                      <summary className="cursor-pointer text-[11px] font-semibold tracking-wide text-neutral-500 uppercase">
                        AI Receipt
                      </summary>
                      <div className="mt-2 space-y-2 text-xs text-neutral-600">
                        <p>
                          <span className="font-medium text-neutral-800">Model:</span>{" "}
                          {msg.receipt.model || "—"}
                        </p>
                        {msg.receipt.ab_variant && (
                          <p>
                            <span className="font-medium text-neutral-800">A/B:</span>{" "}
                            {msg.receipt.ab_variant} ({msg.receipt.ab_model})
                          </p>
                        )}
                        <p>
                          <span className="font-medium text-neutral-800">RAG:</span>{" "}
                          {msg.receipt.rag_used
                            ? `${msg.receipt.source_count} source(s)`
                            : "Not used"}
                        </p>
                        {msg.receipt.sources?.length > 0 && (
                          <p className="text-neutral-500">{msg.receipt.sources.join(" · ")}</p>
                        )}
                        {msg.receipt.chunks?.length > 0 && (
                          <ul className="space-y-1.5">
                            {msg.receipt.chunks.slice(0, 3).map((c, i) => (
                              <li
                                key={i}
                                className="rounded-lg bg-neutral-50 px-2.5 py-2 text-[11px] leading-relaxed"
                              >
                                <span className="font-medium">{c.file_name}</span>
                                {c.score != null && (
                                  <span className="text-neutral-400"> · score {c.score}</span>
                                )}
                                <p className="mt-0.5 text-neutral-500">{c.preview}</p>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </details>
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
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-neutral-200/80 bg-white/90 text-[10px] font-bold text-neutral-500 shadow-sm">
                NF
              </div>
              <div className="chat-bubble-assistant flex items-center gap-2 px-4 py-3.5 text-sm text-neutral-500">
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
            className="rounded-xl border border-red-200/80 bg-red-50/95 px-4 py-3 text-sm text-red-700 shadow-sm"
          >
            {error}
          </motion.div>
        )}

        <div ref={bottomRef} className="h-px shrink-0" />
      </div>
    </div>
  );
}
