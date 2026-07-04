"use client";

import { useEffect, useRef } from "react";

const suggestions = [
  "Summarize my documents",
  "Write a short email",
  "Explain step by step",
  "What can you do?",
];

export default function ChatMessages({ messages, streaming, error, assistantName, onSuggest }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming, error]);

  const showThinking =
    streaming && messages.length > 0 && messages[messages.length - 1]?.role === "user";

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-5 px-4 py-6 sm:px-6">
        {messages.length === 0 && !error && (
          <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-neutral-900 text-xs font-bold text-white">
              NF
            </div>
            <h2 className="text-xl font-semibold tracking-tight text-neutral-900">
              {assistantName || "NovaFlow Assistant"}
            </h2>
            <p className="mt-2 max-w-sm text-sm text-neutral-500">
              Ask a question below or pick a starter prompt.
            </p>

            <div className="mt-8 flex w-full max-w-md flex-wrap justify-center gap-2">
              {suggestions.map((text) => (
                <button
                  key={text}
                  type="button"
                  onClick={() => onSuggest?.(text)}
                  className="rounded-full border border-neutral-200 bg-white px-3.5 py-2 text-xs text-neutral-700 transition-colors hover:border-neutral-400 hover:bg-neutral-50"
                >
                  {text}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-neutral-900 text-[9px] font-bold text-white">
                NF
              </div>
            )}

            <div className={`max-w-[85%] sm:max-w-[75%] ${msg.role === "user" ? "text-right" : ""}`}>
              {msg.role === "assistant" && (
                <p className="mb-1 text-[11px] font-medium text-neutral-400">
                  {assistantName || "Assistant"}
                </p>
              )}
              <div
                className={`text-sm leading-relaxed sm:text-[15px] ${
                  msg.role === "user"
                    ? "inline-block rounded-2xl rounded-tr-sm bg-white/90 px-4 py-3 text-neutral-900 shadow-sm backdrop-blur-sm ring-1 ring-black/5"
                    : "text-neutral-800"
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
                        className="h-1 w-1 animate-bounce rounded-full bg-neutral-400"
                        style={{ animationDelay: `${i * 120}ms` }}
                      />
                    ))}
                  </span>
                )}
                {msg.streaming && msg.content && (
                  <span className="ml-0.5 inline-block h-3.5 w-px animate-pulse bg-neutral-400 align-middle" />
                )}
              </div>
            </div>
          </div>
        ))}

        {showThinking && (
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-neutral-200 text-[9px] font-bold text-neutral-500">
              NF
            </div>
            <div className="flex items-center gap-2 py-2 text-sm text-neutral-500">
              <span className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1 w-1 animate-bounce rounded-full bg-neutral-400"
                    style={{ animationDelay: `${i * 140}ms` }}
                  />
                ))}
              </span>
              Thinking…
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div ref={bottomRef} className="h-px shrink-0" />
      </div>
    </div>
  );
}
