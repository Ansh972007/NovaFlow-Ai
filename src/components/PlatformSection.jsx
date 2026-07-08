"use client";

import Link from "next/link";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import TiltCard from "./TiltCard";
import Magnetic from "./Magnetic";

const ease = [0.16, 1, 0.3, 1];

const tabs = [
  { id: "chat", label: "Chat" },
  { id: "rag", label: "Knowledge" },
  { id: "workflow", label: "Workflows" },
  { id: "team", label: "Teams" },
];

const features = [
  {
    id: "chat",
    title: "Intelligent chat",
    desc: "Streaming responses with memory, tool use, and multi-turn context — built for real conversations.",
    tag: "Core",
    span: "md:col-span-2 md:row-span-2",
    highlights: ["Real-time streaming", "Tool calling", "Session memory"],
  },
  {
    id: "rag",
    title: "Knowledge RAG",
    desc: "Upload docs, embed automatically, and ground every answer in your actual content.",
    tag: "Search",
    span: "",
    highlights: ["PDF & docs", "Vector search", "Citations"],
  },
  {
    id: "workflow",
    title: "Workflow engine",
    desc: "Chain models, APIs, and logic into automated pipelines that run on triggers.",
    tag: "Automate",
    span: "",
    highlights: ["Multi-step flows", "Webhooks", "Scheduling"],
  },
  {
    id: "team",
    title: "Team controls",
    desc: "Roles, permissions, audit logs, and enterprise security — ready for your org.",
    tag: "Enterprise",
    span: "md:col-span-2",
    highlights: ["RBAC", "Audit trail", "SSO ready"],
  },
];

const capabilities = [
  "Unified workspace",
  "OpenAI-compatible",
  "WebSocket streaming",
  "Local & cloud models",
];

function ChatPreview() {
  const msgs = [
    { role: "user", text: "Summarize Q3 updates" },
    { role: "ai", text: "Found 3 policy changes in your knowledge base…" },
    { role: "user", text: "Draft a FAQ" },
  ];
  return (
    <div className="mt-6 space-y-2.5">
      {msgs.map((m, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: m.role === "user" ? 12 : -12 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 + i * 0.15, ease }}
          className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[85%] rounded-xl px-3 py-2 text-[11px] leading-relaxed ${
              m.role === "user"
                ? "rounded-tr-sm bg-black text-white"
                : "rounded-tl-sm border border-border bg-white text-foreground"
            }`}
          >
            {m.text}
          </div>
        </motion.div>
      ))}
      <motion.div
        animate={{ opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.5, repeat: Infinity }}
        className="flex items-center gap-2 pl-1 text-[10px] text-muted"
      >
        <span className="h-1 w-1 rounded-full bg-green-500" />
        AI typing…
      </motion.div>
    </div>
  );
}

function RAGPreview() {
  const docs = ["Policy.pdf", "FAQ.docx", "Guide.md"];
  return (
    <div className="mt-5 space-y-2">
      {docs.map((doc, i) => (
        <motion.div
          key={doc}
          initial={{ opacity: 0, x: -10 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 + i * 0.1, ease }}
          className="flex items-center gap-2 rounded-lg border border-border bg-white px-3 py-2"
        >
          <span className="flex h-6 w-6 items-center justify-center rounded bg-surface text-[10px]">📄</span>
          <span className="flex-1 truncate text-[11px] font-medium">{doc}</span>
          <span className="rounded-full bg-green-50 px-2 py-0.5 text-[9px] font-medium text-green-700">
            indexed
          </span>
        </motion.div>
      ))}
    </div>
  );
}

function WorkflowPreview() {
  const steps = [
    { label: "Trigger", color: "border-emerald-300 bg-emerald-50 text-emerald-800" },
    { label: "Retrieve", color: "border-sky-300 bg-sky-50 text-sky-800" },
    { label: "LLM", color: "border-violet-300 bg-violet-50 text-violet-800" },
    { label: "Notify", color: "border-amber-300 bg-amber-50 text-amber-800" },
    { label: "Output", color: "border-neutral-300 bg-neutral-50 text-neutral-700" },
  ];

  return (
    <div className="relative mt-5 overflow-hidden rounded-xl border border-border bg-gradient-to-br from-surface to-white p-3">
      <div className="mb-2 flex items-center justify-between text-[9px] font-semibold tracking-wider text-muted uppercase">
        <span>Pipeline preview</span>
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="flex items-center gap-1 text-emerald-600"
        >
          <span className="h-1 w-1 rounded-full bg-emerald-500" />
          Live
        </motion.span>
      </div>
      <div className="flex items-center justify-between gap-0.5">
        {steps.map((step, i) => (
          <div key={step.label} className="flex flex-1 items-center">
            <motion.div
              initial={{ scale: 0.7, opacity: 0, y: 8 }}
              whileInView={{ scale: 1, opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.15 + i * 0.1, type: "spring", stiffness: 260, damping: 20 }}
              whileHover={{ scale: 1.06, y: -2 }}
              className={`flex flex-1 flex-col items-center`}
            >
              <div
                className={`flex h-9 w-full max-w-[48px] items-center justify-center rounded-lg border text-[8px] font-bold shadow-sm transition-shadow hover:shadow-md ${step.color}`}
              >
                {step.label}
              </div>
            </motion.div>
            {i < steps.length - 1 && (
              <motion.div
                className="relative mx-0.5 flex h-px flex-1 items-center"
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.25 + i * 0.12, duration: 0.5, ease }}
              >
                <span className="h-px w-full bg-border" />
                <motion.span
                  animate={{ x: ["-100%", "200%"], opacity: [0, 1, 0] }}
                  transition={{ duration: 1.8, repeat: Infinity, delay: i * 0.35, ease: "easeInOut" }}
                  className="absolute h-1 w-3 rounded-full bg-violet-400"
                />
              </motion.div>
            )}
          </div>
        ))}
      </div>
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.7, duration: 0.5 }}
        className="mt-2.5 flex gap-1"
      >
        {["9 templates", "Webhooks", "Cron"].map((tag, i) => (
          <motion.span
            key={tag}
            initial={{ opacity: 0, x: -6 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.75 + i * 0.06 }}
            className="rounded-full bg-white px-2 py-0.5 text-[8px] font-medium text-muted shadow-sm"
          >
            {tag}
          </motion.span>
        ))}
      </motion.div>
    </div>
  );
}

function TeamPreview() {
  const members = ["AK", "SC", "MW", "ER", "+3"];
  return (
    <div className="mt-5">
      <div className="flex -space-x-2">
        {members.map((m, i) => (
          <motion.span
            key={m}
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.15 + i * 0.08, ease }}
            className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-black text-[10px] font-bold text-white"
          >
            {m}
          </motion.span>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {["Admin", "Editor", "Viewer"].map((role) => (
          <span
            key={role}
            className="rounded-full border border-border bg-white px-2.5 py-1 text-[10px] font-medium text-muted"
          >
            {role}
          </span>
        ))}
      </div>
    </div>
  );
}

function FeatureVisual({ id }) {
  if (id === "chat") return <ChatPreview />;
  if (id === "rag") return <RAGPreview />;
  if (id === "workflow") return <WorkflowPreview />;
  if (id === "team") return <TeamPreview />;
  return null;
}

export default function PlatformSection() {
  const [active, setActive] = useState("chat");

  return (
    <section id="bento" className="relative px-4 py-28 sm:px-6">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.7, ease }}
            className="max-w-2xl"
          >
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-white/90 px-4 py-1.5 text-[10px] font-bold tracking-[0.2em] uppercase shadow-sm backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-black" />
              Platform
            </div>
            <h2
              id="features"
              className="font-serif text-4xl leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.25rem]"
            >
              Everything in one
              <br />
              <span className="text-gradient italic">elegant system.</span>
            </h2>
            <p className="mt-5 max-w-lg text-base leading-relaxed text-muted sm:text-lg">
              Chat, knowledge bases, workflows, and team controls — unified in a
              single workspace designed for clarity and speed.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.15, duration: 0.6, ease }}
            className="flex flex-wrap gap-2 lg:justify-end"
          >
            {capabilities.map((cap) => (
              <span
                key={cap}
                className="rounded-full border border-border bg-white/80 px-3.5 py-1.5 text-xs font-medium text-muted shadow-sm backdrop-blur-sm"
              >
                {cap}
              </span>
            ))}
          </motion.div>
        </div>

        {/* Interactive tabs */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2, duration: 0.5, ease }}
          className="mt-12 flex flex-wrap gap-2"
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActive(tab.id)}
              className={`relative rounded-full px-5 py-2.5 text-sm font-semibold transition-all duration-300 ${
                active === tab.id
                  ? "text-white"
                  : "border border-border bg-white/80 text-muted hover:border-foreground/30 hover:text-foreground"
              }`}
            >
              {active === tab.id && (
                <motion.span
                  layoutId="platform-tab"
                  className="absolute inset-0 rounded-full bg-black shadow-lg"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative z-10">{tab.label}</span>
            </button>
          ))}
        </motion.div>

        {/* Bento grid */}
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3 md:auto-rows-[minmax(180px,auto)]">
          {features.map((item, i) => {
            const isActive = active === item.id;
            const isLarge = item.id === "chat";

            return (
              <TiltCard
                key={item.id}
                className={`${item.span} ${isLarge ? "min-h-[360px] md:min-h-0" : ""}`}
              >
                <motion.article
                  layout
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08, duration: 0.6, ease }}
                  onMouseEnter={() => setActive(item.id)}
                  className={`card card-interactive group relative flex h-full flex-col overflow-hidden p-6 transition-all duration-500 sm:p-8 ${
                    isActive
                      ? "border-foreground/20 bg-white shadow-[0_32px_80px_rgba(0,0,0,0.1)] ring-1 ring-black/5"
                      : "card-hover opacity-90 hover:opacity-100"
                  }`}
                  onMouseMove={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    e.currentTarget.style.setProperty("--mouse-x", `${e.clientX - rect.left}px`);
                    e.currentTarget.style.setProperty("--mouse-y", `${e.clientY - rect.top}px`);
                  }}
                >
                  <div className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-surface to-transparent transition-transform duration-700 group-hover:scale-125" />

                  <div className="relative flex items-start justify-between gap-3">
                    <span className="rounded-full border border-border bg-surface px-2.5 py-0.5 text-[10px] font-bold tracking-wider uppercase">
                      {item.tag}
                    </span>
                    <AnimatePresence>
                      {isActive && (
                        <motion.span
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0, opacity: 0 }}
                          className="flex h-2 w-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"
                        />
                      )}
                    </AnimatePresence>
                  </div>

                  <div className="relative mt-4 flex-1">
                    <h3 className={`font-semibold tracking-tight ${isLarge ? "text-2xl sm:text-3xl" : "text-lg"}`}>
                      {item.title}
                    </h3>
                    <p className={`mt-2 text-muted ${isLarge ? "max-w-md text-base leading-relaxed" : "text-sm leading-relaxed"}`}>
                      {item.desc}
                    </p>

                    <ul className={`mt-4 flex flex-wrap gap-2 ${isLarge ? "" : "hidden sm:flex"}`}>
                      {item.highlights.map((h) => (
                        <li
                          key={h}
                          className="flex items-center gap-1.5 rounded-full bg-surface px-2.5 py-1 text-[10px] font-medium text-foreground"
                        >
                          <span className="text-green-600">✓</span>
                          {h}
                        </li>
                      ))}
                    </ul>

                    <FeatureVisual id={item.id} />
                  </div>

                  {isLarge && (
                    <div className="relative mt-6 border-t border-border pt-4">
                      <div className="flex items-center justify-between text-[10px] text-muted">
                        <span>Response quality</span>
                        <span className="font-mono font-medium text-foreground">98.7%</span>
                      </div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: "98.7%" }}
                          viewport={{ once: true }}
                          transition={{ delay: 0.6, duration: 1.2, ease }}
                          className="h-full rounded-full bg-black"
                        />
                      </div>
                    </div>
                  )}
                </motion.article>
              </TiltCard>
            );
          })}
        </div>

        {/* Bottom CTA row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3, duration: 0.6, ease }}
          className="mt-12 flex flex-col items-center justify-between gap-6 rounded-[1.5rem] border border-border bg-white/80 p-6 backdrop-blur-xl sm:flex-row sm:p-8"
        >
          <div>
            <p className="font-semibold">Ready to explore the platform?</p>
            <p className="mt-1 text-sm text-muted">
              Start free — set up your first assistant in under 2 minutes.
            </p>
          </div>
          <Magnetic strength={0.25}>
            <Link href="/login?mode=register" className="group btn-primary shrink-0">
              Get started free
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
          </Magnetic>
        </motion.div>
      </div>
    </section>
  );
}
