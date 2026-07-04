"use client";

import { motion, AnimatePresence } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

export default function ChatMessages({ messages, streaming, error }) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-6 sm:px-8">
      {messages.length === 0 && !error && (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease }}
          className="flex flex-1 flex-col items-center justify-center text-center"
        >
          <div className="relative mb-6">
            <span className="absolute inset-0 animate-pulse rounded-full bg-black/5" />
            <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-black text-xl font-bold text-white">
              NF
            </div>
          </div>
          <p className="font-serif text-2xl tracking-tight">Start a conversation</p>
          <p className="mt-2 max-w-sm text-sm text-muted">
            Messages stream in real time from your connected assistant.
          </p>
        </motion.div>
      )}

      <AnimatePresence initial={false}>
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 12, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.35, ease }}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[70%] ${
                msg.role === "user"
                  ? "rounded-tr-md bg-black text-white shadow-lg shadow-black/10"
                  : "rounded-tl-md border border-border bg-white text-foreground shadow-sm"
              }`}
            >
              <p className="whitespace-pre-wrap break-words">
                {msg.content || (msg.streaming ? "…" : "")}
              </p>
              {msg.streaming && (
                <span className="mt-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current opacity-60" />
              )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {streaming && messages[messages.length - 1]?.role === "user" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex justify-start"
        >
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-muted">
            <span className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </span>
            Thinking…
          </div>
        </motion.div>
      )}

      {error && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {error}
        </motion.div>
      )}
    </div>
  );
}
