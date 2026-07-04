"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const messages = [
  { role: "user", text: "Summarize our Q3 policy updates for the support team." },
  { role: "ai", text: "Based on your knowledge base, I found 3 key policy changes affecting refund windows, SLA tiers, and escalation paths…" },
  { role: "user", text: "Draft a customer-facing FAQ from this." },
  { role: "ai", text: "Here's a concise FAQ with 5 questions covering the most common support scenarios…" },
];

export default function HeroMockup() {
  const [step, setStep] = useState(0);
  const [typed, setTyped] = useState("");
  const current = messages[step];

  useEffect(() => {
    if (!current || current.role !== "ai") return;

    let i = 0;
    setTyped("");
    const text = current.text;
    const interval = setInterval(() => {
      i++;
      setTyped(text.slice(0, i));
      if (i >= text.length) clearInterval(interval);
    }, 18);

    return () => clearInterval(interval);
  }, [step, current]);

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((s) => (s + 1) % messages.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="gradient-border shadow-[0_32px_80px_rgba(0,0,0,0.12)]">
      <div className="relative overflow-hidden rounded-[1.2rem] bg-[#fafafa]">
        {/* Window chrome */}
        <div className="flex items-center justify-between border-b border-border bg-white px-4 py-3">
          <div className="flex gap-2">
            <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
            <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
            <span className="h-3 w-3 rounded-full bg-[#28c840]" />
          </div>
          <span className="text-[11px] font-medium tracking-wide text-muted uppercase">
            NovaFlow Chat
          </span>
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
            </span>
            <span className="text-[10px] text-muted">Live</span>
          </div>
        </div>

        {/* Chat area */}
        <div className="min-h-[280px] space-y-4 p-5 sm:p-6">
          <AnimatePresence mode="wait">
            {messages.slice(0, step + 1).map((msg, idx) => (
              <motion.div
                key={`${idx}-${msg.text.slice(0, 20)}`}
                initial={{ opacity: 0, y: 12, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[88%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed sm:text-sm ${
                    msg.role === "user"
                      ? "rounded-tr-md bg-black text-white"
                      : "rounded-tl-md border border-border bg-white text-foreground shadow-sm"
                  }`}
                >
                  {idx === step && msg.role === "ai" ? (
                    <>
                      {typed}
                      <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-black align-middle" />
                    </>
                  ) : (
                    msg.text
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Input bar mock */}
        <div className="border-t border-border bg-white p-4">
          <div className="flex items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3">
            <span className="flex-1 text-sm text-muted-light">Ask anything…</span>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-black text-xs text-white">
              ↑
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
