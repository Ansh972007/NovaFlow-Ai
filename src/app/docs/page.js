"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";

const ease = [0.16, 1, 0.3, 1];

const sections = [
  {
    title: "Quick start",
    icon: "🚀",
    steps: [
      { n: "01", text: "Start NovaFlow API", code: ".\\deploy\\start-backend.ps1" },
      { n: "02", text: "Configure env", code: "cp .env.example .env.local" },
      { n: "03", text: "Run frontend", code: "npm run dev" },
      { n: "04", text: "Open app", code: "http://localhost:3000" },
      { n: "05", text: "Verify pipelines", code: "npm run verify" },
    ],
  },
  {
    title: "Authentication",
    icon: "🔐",
    steps: [
      { n: "01", text: "Register at", link: "/login?mode=register", linkLabel: "/login?mode=register" },
      { n: "02", text: "Default admin (local): admin / admin123 — change in production" },
      { n: "03", text: "Login uses RSA encryption for secure password transfer" },
      { n: "04", text: "Token stored in localStorage as nf_token; expired sessions redirect to login" },
    ],
  },
  {
    title: "Core pipelines",
    icon: "⚙️",
    steps: [
      { n: "01", text: "Chat", link: "/chat", linkLabel: "/chat" },
      { n: "02", text: "Knowledge + RAG", link: "/knowledge", linkLabel: "/knowledge" },
      { n: "03", text: "Workflows, Runs, Digests", link: "/workflows", linkLabel: "/workflows" },
      { n: "04", text: "Agents & Evaluation", link: "/agents", linkLabel: "/agents" },
      { n: "05", text: "Integrations & Model Lab", link: "/settings", linkLabel: "/settings" },
    ],
  },
  {
    title: "Developer checks",
    icon: "🧪",
    steps: [
      { n: "01", text: "API console presets", link: "/developer", linkLabel: "/developer" },
      { n: "02", text: "Backend smoke tests", code: "cd backend && python -m pytest -q" },
      { n: "03", text: "Health: GET /health → version 9.6.0" },
    ],
  },
];

export default function DocsPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />

      <div className="relative z-10">
        <AppHeader links={[{ href: "/", label: "Home" }, { href: "/login", label: "Sign in" }]} />

        <main className="workspace-page-main mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16">
          <WorkspaceHero
            eyebrow="Documentation"
            title="Getting"
            titleHighlight="started"
            description="Everything you need to run NovaFlow AI locally and connect to your backend."
          />

          <div className="mt-10 space-y-6">
            {sections.map((section, si) => (
              <motion.section
                key={section.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: si * 0.08, ease }}
                className="workspace-panel rounded-[1.75rem] p-6 sm:p-8"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-100 text-lg">
                    {section.icon}
                  </span>
                  <h2 className="text-lg font-semibold tracking-tight">{section.title}</h2>
                </div>
                <ol className="mt-6 space-y-4">
                  {section.steps.map((step) => (
                    <li key={step.n} className="flex gap-4 text-sm leading-relaxed">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-[10px] font-mono text-white">
                        {step.n}
                      </span>
                      <div className="min-w-0 pt-0.5 text-neutral-600">
                        {step.code ? (
                          <>
                            {step.text}
                            <code className="workspace-code-block">{step.code}</code>
                          </>
                        ) : step.link ? (
                          <>
                            {step.text}{" "}
                            <Link href={step.link} className="font-semibold text-neutral-900 underline-offset-2 hover:underline">
                              {step.linkLabel}
                            </Link>
                          </>
                        ) : (
                          step.text
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              </motion.section>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, ease }}
            className="mt-10 text-center"
          >
            <Link href="/login?mode=register" className="btn-primary">
              Create account →
            </Link>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
