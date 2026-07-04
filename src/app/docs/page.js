"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import LiveBackground from "@/components/LiveBackground";

const ease = [0.16, 1, 0.3, 1];

const sections = [
  {
    title: "Quick start",
    steps: [
      { n: "01", text: "Start backend", code: "docker compose -p bisheng up -d" },
      { n: "02", text: "Configure env", code: "cp .env.example .env.local" },
      { n: "03", text: "Run frontend", code: "npm run dev" },
      { n: "04", text: "Open app", code: "http://localhost:3000" },
    ],
  },
  {
    title: "Authentication",
    steps: [
      { n: "01", text: "Register at", link: "/login?mode=register", linkLabel: "/login?mode=register" },
      { n: "02", text: "Login uses RSA encryption for secure password transfer" },
      { n: "03", text: "Token stored in localStorage as nf_token" },
    ],
  },
  {
    title: "Chat",
    steps: [
      { n: "01", text: "Navigate to /chat after signing in" },
      { n: "02", text: "Select an assistant from the sidebar" },
      { n: "03", text: "Messages stream via WebSocket in real time" },
    ],
  },
];

export default function DocsPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <LiveBackground variant="subtle" showNetwork mouseTracking />

      <div className="relative z-10">
        <AppHeader links={[{ href: "/", label: "Home" }, { href: "/login", label: "Sign in" }]} />

        <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
          >
            <p className="text-xs font-semibold tracking-[0.2em] text-muted uppercase">
              Documentation
            </p>
            <h1 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
              Getting started
            </h1>
            <p className="mt-4 text-muted leading-relaxed">
              Everything you need to run NovaFlow AI locally and connect to your backend.
            </p>
          </motion.div>

          <div className="mt-12 space-y-8">
            {sections.map((section, si) => (
              <motion.section
                key={section.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: si * 0.1, duration: 0.6, ease }}
                className="glass-card rounded-2xl p-6 sm:p-8"
              >
                <h2 className="font-semibold text-lg">{section.title}</h2>
                <ol className="mt-6 space-y-4">
                  {section.steps.map((step) => (
                    <li key={step.n} className="flex gap-4 text-sm leading-relaxed">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-black text-[10px] font-mono text-white">
                        {step.n}
                      </span>
                      <div className="pt-0.5">
                        {step.code ? (
                          <>
                            {step.text}:{" "}
                            <code className="mt-1 block rounded-lg bg-surface px-3 py-2 font-mono text-xs">
                              {step.code}
                            </code>
                          </>
                        ) : step.link ? (
                          <>
                            {step.text}{" "}
                            <Link href={step.link} className="font-medium underline underline-offset-4">
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
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="mt-12 text-center"
          >
            <Link href="/login?mode=register" className="btn-primary">
              Create account →
            </Link>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
