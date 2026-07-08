"use client";

import Link from "next/link";
import { useRef } from "react";
import { motion, useInView, useScroll, useTransform } from "framer-motion";
import LiveBackground from "@/components/LiveBackground";
import Magnetic from "@/components/Magnetic";

const ease = [0.16, 1, 0.3, 1];

const steps = [
  {
    n: "01",
    title: "Connect",
    desc: "Link models, APIs, Telegram, Gmail, and your knowledge bases in minutes.",
    icon: "⚡",
    color: "from-emerald-500/20 to-emerald-500/5",
    ring: "border-emerald-400/40",
  },
  {
    n: "02",
    title: "Build",
    desc: "Drag nodes in the visual studio — RAG, agents, notify, loops, and human review.",
    icon: "◆",
    color: "from-violet-500/20 to-violet-500/5",
    ring: "border-violet-400/40",
  },
  {
    n: "03",
    title: "Deploy",
    desc: "Publish workflows, register webhooks, schedule cron runs, and ship to your team.",
    icon: "▶",
    color: "from-sky-500/20 to-sky-500/5",
    ring: "border-sky-400/40",
  },
];

const pipelineNodes = [
  { id: "trigger", label: "Trigger", x: 8, color: "#10b981" },
  { id: "retrieve", label: "Retrieve", x: 30, color: "#0ea5e9" },
  { id: "llm", label: "LLM", x: 52, color: "#8b5cf6" },
  { id: "notify", label: "Notify", x: 74, color: "#f59e0b" },
  { id: "output", label: "Output", x: 92, color: "#737373" },
];

function PipelineViz({ active }) {
  return (
    <div className="relative mx-auto mt-16 max-w-3xl overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-sm sm:p-8">
      <div className="mb-4 flex items-center justify-between text-[10px] font-semibold tracking-[0.2em] text-neutral-500 uppercase">
        <span>Live pipeline</span>
        <motion.span
          animate={{ opacity: active ? [0.5, 1, 0.5] : 0.5 }}
          transition={{ duration: 2, repeat: Infinity }}
          className="flex items-center gap-1.5 text-emerald-400"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Running
        </motion.span>
      </div>

      <svg viewBox="0 0 400 100" className="w-full" aria-hidden>
        <defs>
          <linearGradient id="wf-flow-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.8" />
          </linearGradient>
        </defs>

        {pipelineNodes.slice(0, -1).map((node, i) => {
          const x1 = node.x * 4;
          const x2 = pipelineNodes[i + 1].x * 4;
          return (
            <g key={`edge-${node.id}`}>
              <line x1={x1} y1="50" x2={x2} y2="50" stroke="rgba(255,255,255,0.08)" strokeWidth="2" />
              <motion.line
                x1={x1}
                y1="50"
                x2={x2}
                y2="50"
                stroke="url(#wf-flow-grad)"
                strokeWidth="2"
                strokeDasharray="6 8"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={active ? { pathLength: 1, opacity: 1, strokeDashoffset: [0, -28] } : { pathLength: 0, opacity: 0 }}
                transition={{
                  pathLength: { duration: 0.8, delay: 0.3 + i * 0.15, ease },
                  opacity: { duration: 0.4, delay: 0.3 + i * 0.15 },
                  strokeDashoffset: { duration: 1.2, repeat: Infinity, ease: "linear", delay: i * 0.2 },
                }}
              />
              <motion.circle
                r="3"
                fill="#fff"
                initial={{ opacity: 0 }}
                animate={
                  active
                    ? {
                        opacity: [0, 1, 1, 0],
                        cx: [x1, x2],
                        cy: 50,
                      }
                    : { opacity: 0 }
                }
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: i * 0.5,
                  ease: "easeInOut",
                }}
              />
            </g>
          );
        })}

        {pipelineNodes.map((node, i) => (
          <motion.g
            key={node.id}
            initial={{ opacity: 0, scale: 0.6 }}
            animate={active ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.6 }}
            transition={{ delay: 0.15 + i * 0.1, duration: 0.5, ease }}
          >
            <circle
              cx={node.x * 4}
              cy="50"
              r="18"
              fill="rgba(255,255,255,0.04)"
              stroke={node.color}
              strokeWidth="1.5"
              opacity="0.9"
            />
            <motion.circle
              cx={node.x * 4}
              cy="50"
              r="22"
              fill="none"
              stroke={node.color}
              strokeWidth="1"
              opacity="0.35"
              animate={active ? { r: [22, 28, 22], opacity: [0.35, 0, 0.35] } : {}}
              transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.35 }}
            />
            <text
              x={node.x * 4}
              y="82"
              textAnchor="middle"
              fill="rgba(255,255,255,0.55)"
              fontSize="9"
              fontWeight="500"
            >
              {node.label}
            </text>
          </motion.g>
        ))}
      </svg>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={active ? { opacity: 1, y: 0 } : {}}
        transition={{ delay: 0.9, duration: 0.5, ease }}
        className="mt-4 flex flex-wrap gap-2"
      >
        {["Telegram Q&A", "Daily digest", "Eval alerts", "RAG pipeline"].map((tpl, i) => (
          <motion.span
            key={tpl}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={active ? { opacity: 1, scale: 1 } : {}}
            transition={{ delay: 1 + i * 0.08, ease }}
            whileHover={{ scale: 1.04, borderColor: "rgba(255,255,255,0.35)" }}
            className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[10px] font-medium text-neutral-300 transition-colors"
          >
            {tpl}
          </motion.span>
        ))}
      </motion.div>
    </div>
  );
}

export default function WorkflowShowcase() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const parallaxY = useTransform(scrollYProgress, [0, 1], [40, -40]);

  return (
    <section ref={ref} className="section-dark relative overflow-hidden px-4 py-28 sm:px-6">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <LiveBackground variant="dark" showGrid={false} showNetwork={false} />
        <motion.div
          style={{ y: parallaxY }}
          className="absolute -left-32 top-1/4 h-96 w-96 rounded-full bg-violet-500/10 blur-[100px]"
        />
        <motion.div
          style={{ y: useTransform(scrollYProgress, [0, 1], [-30, 30]) }}
          className="absolute -right-24 bottom-1/4 h-80 w-80 rounded-full bg-emerald-500/10 blur-[90px]"
        />
      </div>

      <div className="relative mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, ease }}
          className="max-w-2xl"
        >
          <motion.p
            initial={{ opacity: 0, x: -12 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.1, duration: 0.6, ease }}
            className="text-xs font-semibold tracking-[0.2em] text-neutral-500 uppercase"
          >
            Workflow engine
          </motion.p>
          <h2 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
            <motion.span
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.15, duration: 0.7, ease }}
              className="block"
            >
              From idea to production
            </motion.span>
            <motion.span
              initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
              animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
              transition={{ delay: 0.3, duration: 0.8, ease }}
              className="mt-1 block italic text-neutral-400"
            >
              in three steps.
            </motion.span>
          </h2>
          <motion.p
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.45, duration: 0.6 }}
            className="mt-5 max-w-lg text-sm leading-relaxed text-neutral-400"
          >
            Visual pipelines with 9 starter templates — Telegram bots, email digests, RAG Q&A, and
            eval alerts. No code required.
          </motion.p>
        </motion.div>

        <PipelineViz active={inView} />

        <div className="relative mt-20 grid gap-10 md:grid-cols-3">
          <motion.div
            className="absolute top-10 hidden h-px md:block"
            style={{ left: "16.66%", right: "16.66%" }}
            initial={{ scaleX: 0 }}
            animate={inView ? { scaleX: 1 } : {}}
            transition={{ delay: 0.5, duration: 1.2, ease }}
          >
            <div className="h-full w-full origin-left bg-gradient-to-r from-transparent via-white/25 to-transparent" />
          </motion.div>

          {steps.map((step, i) => (
            <motion.div
              key={step.n}
              initial={{ opacity: 0, y: 40 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.35 + i * 0.15, duration: 0.7, ease }}
              whileHover={{ y: -8, transition: { duration: 0.25 } }}
              className="group relative cursor-default"
            >
              <motion.div
                className={`mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border bg-gradient-to-br ${step.color} ${step.ring} text-lg backdrop-blur-sm transition-shadow duration-500 group-hover:shadow-[0_0_40px_rgba(255,255,255,0.08)]`}
                whileHover={{ rotate: [0, -3, 3, 0], transition: { duration: 0.4 } }}
              >
                <span className="text-sm opacity-90">{step.icon}</span>
                <span className="absolute -right-1 -top-1 rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[9px] text-neutral-400">
                  {step.n}
                </span>
              </motion.div>
              <h3 className="text-xl font-semibold transition-colors group-hover:text-white">
                {step.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-neutral-400 transition-colors group-hover:text-neutral-300">
                {step.desc}
              </p>
              <motion.div
                className="mt-4 h-0.5 w-0 rounded-full bg-gradient-to-r from-white/50 to-transparent"
                whileHover={{ width: "100%" }}
                transition={{ duration: 0.4, ease }}
              />
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.85, duration: 0.6, ease }}
          className="mt-16 flex flex-col items-center justify-center gap-4 sm:flex-row"
        >
          <Magnetic strength={0.3}>
            <Link
              href="/workflows"
              className="group inline-flex items-center gap-2 rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-black transition-all hover:scale-[1.03] hover:shadow-[0_20px_50px_rgba(255,255,255,0.15)]"
            >
              Open workflow studio
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
          </Magnetic>
          <Link
            href="/login?mode=register"
            className="inline-flex items-center rounded-full border border-white/20 px-8 py-3.5 text-sm font-semibold text-white transition-all hover:border-white/40 hover:bg-white/5"
          >
            Start free
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
