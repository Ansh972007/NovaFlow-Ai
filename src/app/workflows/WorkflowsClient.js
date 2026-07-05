"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { getUserInfo } from "@/lib/api/auth";

const ease = [0.16, 1, 0.3, 1];

const templates = [
  {
    id: "rag",
    name: "RAG Q&A pipeline",
    desc: "Ingest docs → embed → retrieve → answer with citations.",
    steps: ["Upload", "Embed", "Retrieve", "Reply"],
  },
  {
    id: "support",
    name: "Support triage",
    desc: "Classify tickets, route to the right assistant, escalate when needed.",
    steps: ["Classify", "Route", "Draft", "Escalate"],
  },
  {
    id: "research",
    name: "Research brief",
    desc: "Multi-step search, summarize sources, produce a structured report.",
    steps: ["Search", "Summarize", "Synthesize", "Export"],
  },
];

export default function WorkflowsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  if (!user) {
    return (
      <div className="relative flex min-h-screen items-center justify-center">
        <WorkspaceLiveBackground />
        <span className="relative z-10 text-neutral-500">Loading…</span>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">
          <WorkspaceHero
            eyebrow="Automate"
            title="Workflow"
            titleHighlight="engine"
            description="Chain models, knowledge, and logic into repeatable pipelines. Visual builder shipping in v0.6."
            badge={<span className="rounded-full bg-neutral-900 px-3 py-1 text-[10px] font-bold tracking-wide text-white uppercase">Preview</span>}
            actions={
              <button type="button" disabled className="btn-primary shrink-0 opacity-50 cursor-not-allowed">
                + New workflow (soon)
              </button>
            }
          />

          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, ease }}
            className="mt-10"
          >
            <p className="workspace-section-label mb-5">Starter templates</p>
            <div className="grid gap-4 md:grid-cols-3">
              {templates.map((tpl, i) => (
                <motion.div
                  key={tpl.id}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 + i * 0.06, ease }}
                  className="workspace-card rounded-2xl p-6"
                >
                  <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-bold uppercase text-neutral-500">
                    Template
                  </span>
                  <h3 className="mt-4 text-lg font-semibold tracking-tight">{tpl.name}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-neutral-500">{tpl.desc}</p>
                  <div className="mt-5 flex flex-wrap gap-1.5">
                    {tpl.steps.map((step, j) => (
                      <span key={step} className="flex items-center gap-1.5">
                        <span className="rounded-md bg-white/80 px-2 py-1 text-[10px] font-semibold text-neutral-700 ring-1 ring-black/5">
                          {step}
                        </span>
                        {j < tpl.steps.length - 1 && (
                          <span className="text-neutral-300">→</span>
                        )}
                      </span>
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.section>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, ease }}
            className="workspace-panel mt-10 rounded-[1.75rem] p-8 sm:p-10"
          >
            <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold tracking-tight">Visual builder</h2>
                <p className="mt-2 max-w-lg text-sm text-neutral-500">
                  Drag nodes, connect triggers, and deploy workflows alongside your assistants.
                  Use Apps + Knowledge today; full workflow runtime lands next.
                </p>
              </div>
              <div className="flex gap-2">
                <Link href="/apps" className="btn-secondary">Manage apps</Link>
                <Link href="/knowledge" className="btn-primary">Knowledge bases</Link>
              </div>
            </div>

            <div className="mt-8 grid grid-cols-4 gap-3 opacity-70">
              {["Trigger", "Retrieve", "LLM", "Output"].map((node, i) => (
                <div
                  key={node}
                  className="rounded-xl border border-dashed border-neutral-300 bg-white/50 px-3 py-6 text-center text-xs font-semibold text-neutral-500"
                  style={{ animationDelay: `${i * 0.1}s` }}
                >
                  {node}
                  {i < 3 && <span className="mt-2 block text-neutral-300">↓</span>}
                </div>
              ))}
            </div>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
