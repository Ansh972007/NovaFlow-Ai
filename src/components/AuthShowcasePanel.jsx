"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Logo from "@/components/Logo";
import HeroMockup from "@/components/HeroMockup";

const ease = [0.16, 1, 0.3, 1];

const highlights = [
  "Deploy AI assistants in minutes",
  "Ground answers in your own documents",
  "Automate workflows across your stack",
];

const steps = [
  { n: "01", title: "Connect", desc: "Link docs, APIs & tools" },
  { n: "02", title: "Configure", desc: "Design automated workflows" },
  { n: "03", title: "Deploy", desc: "Ship to your team instantly" },
];

const features = [
  {
    icon: "◆",
    title: "Smart chat",
    desc: "Streaming AI with memory and tool use",
  },
  {
    icon: "◇",
    title: "Knowledge RAG",
    desc: "Accurate answers from your data",
  },
  {
    icon: "◎",
    title: "Workflows",
    desc: "Multi-step flows with approvals",
  },
  {
    icon: "▣",
    title: "Team spaces",
    desc: "Roles, sharing & audit trails",
  },
];

export default function AuthShowcasePanel({ isRegister = false, greeting = 0 }) {
  const welcomed = greeting > 0;
  const [line, setLine] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setLine((n) => (n + 1) % highlights.length), 3200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative z-10 hidden min-h-screen flex-col justify-center px-8 py-12 md:flex lg:px-12 xl:px-14">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease }}
        className="max-w-xl"
      >
        <Logo size="md" />
        <p className="mt-8 text-[11px] font-semibold uppercase tracking-[0.22em] text-muted">
          {isRegister ? "Get started free" : "Why NovaFlow"}
        </p>
        <h2 className="mt-2 font-serif text-4xl tracking-tight text-foreground lg:text-[2.75rem] lg:leading-[1.1]">
          {isRegister ? "Your AI workspace starts here" : "Everything your team needs"}
        </h2>
        <div className="mt-3 h-6 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.p
              key={line}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4, ease }}
              className="text-sm text-muted"
            >
              {highlights[line]}
            </motion.p>
          </AnimatePresence>
        </div>
      </motion.div>

      <motion.div
        className="mt-8 max-w-xl"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.75, delay: 0.1, ease }}
      >
        <HeroMockup />
      </motion.div>

      <motion.div
        className="mt-8 grid max-w-xl grid-cols-3 gap-3"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, duration: 0.6, ease }}
      >
        {steps.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.08, ease }}
            className="rounded-2xl border border-border bg-white/80 px-4 py-4 shadow-sm backdrop-blur-sm"
          >
            <span className="text-[10px] font-bold text-muted">{s.n}</span>
            <p className="mt-1 text-sm font-semibold text-foreground">{s.title}</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted">{s.desc}</p>
          </motion.div>
        ))}
      </motion.div>

      <motion.div
        className="mt-6 grid max-w-xl grid-cols-2 gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.6 }}
      >
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.45 + i * 0.06, ease }}
            className="flex gap-3 rounded-2xl border border-border bg-white/70 px-4 py-3.5 backdrop-blur-sm transition-shadow hover:shadow-md"
          >
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface text-xs text-muted">
              {f.icon}
            </span>
            <div>
              <p className="text-xs font-semibold text-foreground">{f.title}</p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-muted">{f.desc}</p>
            </div>
          </motion.div>
        ))}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.55, ease }}
        className="mt-8 flex max-w-xl items-center gap-4 rounded-2xl border border-border bg-white/80 px-5 py-4 shadow-sm backdrop-blur-sm"
      >
        <div className="flex -space-x-2">
          {["SK", "JM", "AR", "PL"].map((init) => (
            <span
              key={init}
              className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-surface text-[9px] font-bold text-muted"
            >
              {init}
            </span>
          ))}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm leading-relaxed text-foreground/80">
            &ldquo;NovaFlow cut our support response time in half.&rdquo;
          </p>
          <p className="mt-1 text-[11px] text-muted">Sarah K. · Ops Lead</p>
        </div>
        <div className="hidden shrink-0 text-right sm:block">
          <p className="text-lg font-semibold text-foreground">2.4k+</p>
          <p className="text-[10px] uppercase tracking-wider text-muted">Teams</p>
        </div>
      </motion.div>

      <AnimatePresence>
        {welcomed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center bg-white/50 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.96, y: 16 }}
              animate={{ scale: 1, y: 0 }}
              className="rounded-2xl border border-border bg-white px-8 py-6 text-center shadow-2xl"
            >
              <p className="text-2xl">✓</p>
              <p className="mt-2 font-serif text-xl text-foreground">Welcome to NovaFlow</p>
              <p className="mt-1 text-sm text-muted">Opening your workspace…</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
