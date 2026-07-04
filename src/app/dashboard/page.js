"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import CursorGlow from "@/components/CursorGlow";
import AppHeader from "@/components/AppHeader";
import LiveBackground from "@/components/LiveBackground";
import AnimatedCounter from "@/components/AnimatedCounter";
import { getUserInfo } from "@/lib/api/auth";

const ease = [0.16, 1, 0.3, 1];

const quickLinks = [
  { href: "/chat", label: "Chat", desc: "Talk to your AI assistants", icon: "💬", live: true },
  { href: "#", label: "Knowledge", desc: "Upload & search documents", icon: "📚", live: false },
  { href: "#", label: "Apps", desc: "Manage assistants & flows", icon: "⚡", live: false },
  { href: "#", label: "Settings", desc: "Models & configuration", icon: "⚙️", live: false },
];

const stats = [
  { value: "12", suffix: "", label: "Active chats" },
  { value: "3", suffix: "", label: "Assistants" },
  { value: "98", suffix: "%", label: "Uptime" },
];

export default function DashboardPage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden">
      <CursorGlow />
      <LiveBackground variant="subtle" showNetwork mouseTracking />

      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
            className="glass-card rounded-[1.5rem] p-8 sm:p-10"
          >
            <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-semibold tracking-[0.2em] text-muted uppercase">
                  Workspace
                </p>
                <h1 className="mt-3 font-serif text-4xl tracking-tight sm:text-5xl">
                  Dashboard
                </h1>
                <p className="mt-3 max-w-xl text-muted">
                  {loading
                    ? "Loading your workspace…"
                    : user
                      ? `Welcome back, ${user.user_name}.`
                      : "Sign in to access your AI workspace."}
                </p>
              </div>
              {!loading && user && (
                <Link href="/chat" className="group btn-primary inline-flex shrink-0">
                  Open Chat
                  <span className="transition-transform group-hover:translate-x-0.5">→</span>
                </Link>
              )}
            </div>

            {user && (
              <div className="mt-10 grid grid-cols-3 gap-4 border-t border-border pt-8">
                {stats.map((stat, i) => (
                  <motion.div
                    key={stat.label}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 + i * 0.08, ease }}
                    className="text-center sm:text-left"
                  >
                    <p className="text-2xl font-semibold tabular-nums sm:text-3xl">
                      <AnimatedCounter value={stat.value} suffix={stat.suffix} />
                    </p>
                    <p className="mt-1 text-xs text-muted">{stat.label}</p>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>

          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {quickLinks.map((item, i) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.06, duration: 0.5, ease }}
              >
                {item.live ? (
                  <Link href={item.href} className="glass-card card-hover block rounded-2xl p-6">
                    <div className="flex items-start justify-between">
                      <span className="text-2xl">{item.icon}</span>
                      <span className="rounded-full bg-black px-2.5 py-0.5 text-[10px] font-semibold tracking-wide text-white uppercase">
                        Live
                      </span>
                    </div>
                    <h2 className="mt-4 font-semibold">{item.label}</h2>
                    <p className="mt-1 text-sm text-muted">{item.desc}</p>
                  </Link>
                ) : (
                  <div className="glass-card rounded-2xl p-6 opacity-50">
                    <span className="text-2xl opacity-60">{item.icon}</span>
                    <div className="mt-4 flex items-center justify-between">
                      <h2 className="font-semibold">{item.label}</h2>
                      <span className="text-xs font-medium text-muted">Soon</span>
                    </div>
                    <p className="mt-1 text-sm text-muted">{item.desc}</p>
                  </div>
                )}
              </motion.div>
            ))}
          </div>

          {!loading && !user && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, ease }}
              className="mt-10 text-center"
            >
              <Link href="/login" className="btn-primary">
                Sign in to get started
              </Link>
            </motion.div>
          )}
        </main>
      </div>
    </div>
  );
}
