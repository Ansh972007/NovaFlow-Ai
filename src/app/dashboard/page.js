"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Logo from "@/components/Logo";
import { getUserInfo } from "@/lib/api/auth";

const quickLinks = [
  { href: "#", label: "Chat", desc: "Talk to your AI apps", badge: "Soon" },
  {
    href: "#",
    label: "Knowledge",
    desc: "Upload & search documents",
    badge: "Soon",
  },
  {
    href: "#",
    label: "Apps",
    desc: "Manage assistants & flows",
    badge: "Soon",
  },
  {
    href: "#",
    label: "Settings",
    desc: "Models & workspace config",
    badge: "Soon",
  },
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
    <div className="min-h-full bg-background">
      <header className="border-b border-nova-border bg-nova-surface">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo size="sm" />
          <div className="flex items-center gap-4">
            {!loading && user && (
              <span className="hidden text-sm text-nova-muted sm:inline">
                {user.user_name}
              </span>
            )}
            <Link
              href="/login"
              className="text-sm font-medium text-nova-muted hover:text-foreground"
            >
              {user ? "Account" : "Sign in"}
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="rounded-2xl border border-nova-border bg-nova-surface p-8">
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
            v0.1 checkpoint
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-2 max-w-xl text-nova-muted">
            {loading
              ? "Loading workspace…"
              : user
                ? `Welcome, ${user.user_name}. Your NovaFlow AI workspace is ready.`
                : "Sign in to connect to your backend and unlock the workspace."}
          </p>
          {!loading && !user && (
            <Link
              href="/login"
              className="nova-gradient mt-6 inline-block rounded-lg px-6 py-2.5 text-sm font-semibold text-white"
            >
              Sign in
            </Link>
          )}
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {quickLinks.map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-nova-border bg-nova-surface p-5 opacity-90"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">{item.label}</h2>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-nova-muted dark:bg-slate-800">
                  {item.badge}
                </span>
              </div>
              <p className="mt-2 text-sm text-nova-muted">{item.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
