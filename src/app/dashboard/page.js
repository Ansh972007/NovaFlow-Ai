"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import AnalyticsCharts from "@/components/dashboard/AnalyticsCharts";
import AnimatedCounter from "@/components/AnimatedCounter";
import { getUserInfo } from "@/lib/api/auth";
import { getOnlineApps, getAssistants } from "@/lib/api/apps";
import { getAnalyticsSummary, getAnalyticsTimeseries, getAnalyticsAssistants, getAbRoutingAnalytics } from "@/lib/api/analytics";
import { checkBackendHealth } from "@/lib/api/health";
import { listKnowledge } from "@/lib/api/knowledge";
import { loadSessions } from "@/lib/chat/storage";
import { isSetupComplete } from "@/lib/setup/storage";
import { truncate } from "@/lib/utils";

const ease = [0.16, 1, 0.3, 1];

const modules = [
  {
    href: "/chat",
    label: "Chat",
    desc: "Stream responses with your AI assistants",
    accent: "from-neutral-900 to-neutral-700",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
      </svg>
    ),
  },
  {
    href: "/knowledge",
    label: "Knowledge",
    desc: "Upload docs and power RAG answers",
    accent: "from-neutral-800 to-neutral-600",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    ),
  },
  {
    href: "/apps",
    label: "Apps",
    desc: "Create, publish, and manage assistants",
    accent: "from-neutral-700 to-neutral-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    href: "/workflows",
    label: "Workflows",
    desc: "Automate multi-step AI pipelines",
    accent: "from-neutral-600 to-neutral-400",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="6" cy="6" r="2.5" />
        <circle cx="18" cy="6" r="2.5" />
        <circle cx="12" cy="18" r="2.5" />
        <path d="M8 6h8M7.5 7.5L10.5 16M16.5 7.5L13.5 16" />
      </svg>
    ),
  },
  {
    href: "/agents",
    label: "Agents",
    desc: "Run tool-augmented agents standalone",
    accent: "from-neutral-700 to-neutral-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <rect x="4" y="8" width="16" height="12" rx="2" />
        <path d="M9 8V6a3 3 0 0 1 6 0v2" />
        <circle cx="9" cy="13" r="1" fill="currentColor" />
        <circle cx="15" cy="13" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: "/settings",
    label: "Settings",
    desc: "API health, models, and workspace config",
    accent: "from-neutral-600 to-neutral-400",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
      </svg>
    ),
  },
];

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function formatWhen(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  const diff = Date.now() - d;
  if (diff < 86400000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (diff < 604800000) return d.toLocaleDateString([], { weekday: "short" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [healthOk, setHealthOk] = useState(null);
  const [recentSessions, setRecentSessions] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [chartSeries, setChartSeries] = useState([]);
  const [topAssistants, setTopAssistants] = useState([]);
  const [abRouting, setAbRouting] = useState(null);
  const [stats, setStats] = useState([
    { value: "0", label: "Chat sessions", hint: "Local history" },
    { value: "0", label: "Assistants", hint: "Published & draft" },
    { value: "0", label: "Knowledge bases", hint: "Document libraries" },
    { value: "0", label: "Workflow runs", hint: "Last 7 days" },
  ]);

  const greeting = useMemo(() => getGreeting(), []);

  useEffect(() => {
    if (!isSetupComplete()) {
      router.replace("/setup");
    }
  }, [router]);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        setUser(u);
        const sessions = loadSessions().sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
        setRecentSessions(sessions.slice(0, 5));

        let apps = [];
        try {
          apps = (await getOnlineApps()) || [];
          if (!apps.length) {
            const assistants = await getAssistants();
            apps = assistants || [];
          }
        } catch {
          apps = [];
        }

        let kbTotal = 0;
        let analytics = null;
        try {
          const kb = await listKnowledge({ pageSize: 1 });
          kbTotal = kb?.total || 0;
        } catch {
          kbTotal = 0;
        }

        try {
          const [summary, ts, usage, ab] = await Promise.all([
            getAnalyticsSummary(),
            getAnalyticsTimeseries(7).catch(() => null),
            getAnalyticsAssistants(7).catch(() => null),
            getAbRoutingAnalytics(30).catch(() => null),
          ]);
          analytics = summary;
          setRecentRuns(summary?.recent_runs || []);
          setChartSeries(ts?.series || []);
          setTopAssistants(usage?.items || []);
          setAbRouting(ab);
        } catch {
          analytics = null;
        }

        setStats([
          { value: String(sessions.length), label: "Chat sessions", hint: "Local history" },
          {
            value: String(analytics?.assistants_total ?? apps.length),
            label: "Assistants",
            hint: `${analytics?.assistants_online ?? 0} online`,
          },
          { value: String(analytics?.knowledge_total ?? kbTotal), label: "Knowledge bases", hint: "Document libraries" },
          {
            value: String(analytics?.workflow_runs_7d ?? 0),
            label: "Workflow runs",
            hint: `${analytics?.workflows_published ?? 0} published`,
          },
        ]);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));

    checkBackendHealth()
      .then((h) => setHealthOk(h.ok))
      .catch(() => setHealthOk(false));
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />

      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">
          {/* Hero */}
          <motion.section
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, ease }}
            className="dashboard-hero relative overflow-hidden rounded-[1.75rem] p-8 sm:p-10"
          >
            <div className="dashboard-hero-glow pointer-events-none absolute inset-0" aria-hidden />

            <div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-2xl">
                <motion.div
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1, duration: 0.5, ease }}
                  className="mb-5 inline-flex items-center gap-2.5 rounded-full border border-black/10 bg-white/80 px-4 py-1.5 text-[11px] font-semibold tracking-[0.18em] uppercase backdrop-blur-md"
                >
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-40" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                  </span>
                  <span className="text-emerald-700">Workspace live</span>
                  <span className="text-neutral-400">·</span>
                  <span className="text-neutral-500">NovaFlow AI</span>
                </motion.div>

                <p className="text-sm font-medium text-neutral-500">
                  {loading ? "Loading…" : user ? `${greeting}, ${user.user_name}` : "Welcome"}
                </p>
                <h1 className="mt-2 font-serif text-4xl tracking-tight sm:text-5xl lg:text-[3.25rem]">
                  Your AI{" "}
                  <span className="text-gradient">command center</span>
                </h1>
                <p className="mt-4 max-w-lg text-[15px] leading-relaxed text-neutral-500">
                  Chat, knowledge, and assistants in one place — pick up where you left off or launch something new.
                </p>
              </div>

              {!loading && user && (
                <motion.div
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2, duration: 0.5, ease }}
                  className="flex shrink-0 flex-wrap gap-3"
                >
                  <Link href="/chat" className="group btn-primary inline-flex">
                    Open Chat
                    <span className="transition-transform group-hover:translate-x-1">→</span>
                  </Link>
                  <Link href="/apps" className="btn-secondary">
                    Manage apps
                  </Link>
                </motion.div>
              )}
            </div>

            {user && (
              <div className="relative mt-10 grid gap-4 border-t border-black/[0.06] pt-8 sm:grid-cols-2 lg:grid-cols-4">
                {stats.map((stat, i) => (
                  <motion.div
                    key={stat.label}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 + i * 0.08, ease }}
                    whileHover={{ y: -2 }}
                    className="workspace-stat rounded-2xl p-5"
                  >
                    <p className="text-3xl font-semibold tabular-nums tracking-tight sm:text-4xl">
                      <AnimatedCounter value={stat.value} />
                    </p>
                    <p className="mt-1.5 text-sm font-semibold text-neutral-900">{stat.label}</p>
                    <p className="mt-0.5 text-xs text-neutral-400">{stat.hint}</p>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.section>

          {user && (
            <motion.section
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28, ease }}
              className="mt-8"
            >
              <AnalyticsCharts series={chartSeries} assistants={topAssistants} abRouting={abRouting} />
            </motion.section>
          )}

          <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_320px]">
            {/* Modules */}
            <section>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3, ease }}
                className="mb-5 flex items-end justify-between"
              >
                <div>
                  <p className="text-[11px] font-semibold tracking-[0.2em] text-neutral-400 uppercase">
                    Modules
                  </p>
                  <h2 className="mt-1 text-xl font-semibold tracking-tight">Jump back in</h2>
                </div>
              </motion.div>

              <div className="grid gap-4 sm:grid-cols-2">
                {modules.map((item, i) => (
                  <motion.div
                    key={item.label}
                    initial={{ opacity: 0, y: 18 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.32 + i * 0.06, duration: 0.5, ease }}
                  >
                    <Link href={item.href} className="workspace-card group block rounded-2xl p-6">
                      <div className="flex items-start justify-between">
                        <div className="workspace-icon-tile h-11 w-11 transition-transform duration-300 group-hover:scale-105">
                          {item.icon}
                        </div>
                        <span className="workspace-badge-live !text-neutral-700 before:!bg-neutral-900 before:!shadow-none">
                          Live
                        </span>
                      </div>
                      <h3 className="mt-5 text-lg font-semibold tracking-tight">{item.label}</h3>
                      <p className="mt-1.5 text-sm leading-relaxed text-neutral-500">{item.desc}</p>
                      <p className="mt-4 flex items-center gap-1 text-xs font-semibold text-neutral-900 opacity-0 transition-all duration-300 group-hover:opacity-100">
                        Open module
                        <span className="transition-transform group-hover:translate-x-1">→</span>
                      </p>
                    </Link>
                  </motion.div>
                ))}
              </div>
            </section>

            {/* Sidebar */}
            <aside className="space-y-6">
              <motion.div
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.38, duration: 0.55, ease }}
                className="workspace-panel rounded-2xl p-5"
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold tracking-tight">Recent chats</h2>
                  <Link href="/chat" className="text-xs font-medium text-neutral-500 hover:text-neutral-900">
                    View all
                  </Link>
                </div>

                {!user ? (
                  <p className="mt-4 text-sm text-neutral-500">Sign in to see history.</p>
                ) : recentSessions.length === 0 ? (
                  <div className="mt-4 rounded-xl border border-white/60 bg-white/50 p-4 text-center backdrop-blur-sm">
                    <p className="text-sm text-neutral-500">No chats yet</p>
                    <Link href="/chat" className="mt-2 inline-block text-xs font-semibold hover:underline">
                      Start a conversation →
                    </Link>
                  </div>
                ) : (
                  <ul className="mt-4 space-y-1">
                    {recentSessions.map((session, i) => (
                      <motion.li
                        key={session.id}
                        initial={{ opacity: 0, x: 8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.42 + i * 0.05, ease }}
                      >
                        <Link
                          href={`/chat?app=${session.appId}&session=${session.id}`}
                          className="dashboard-recent-item block rounded-xl px-3 py-2.5"
                        >
                          <p className="truncate text-sm font-medium text-neutral-900">
                            {truncate(session.title || "New chat", 32)}
                          </p>
                          <p className="mt-0.5 flex items-center justify-between text-[11px] text-neutral-400">
                            <span className="truncate">{session.appName || "Assistant"}</span>
                            <span>{formatWhen(session.updatedAt)}</span>
                          </p>
                        </Link>
                      </motion.li>
                    ))}
                  </ul>
                )}
              </motion.div>

              {recentRuns.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.44, duration: 0.55, ease }}
                  className="workspace-panel rounded-2xl p-5"
                >
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold tracking-tight">Workflow activity</h2>
                    <Link href="/workflows" className="text-xs font-medium text-neutral-500 hover:text-neutral-900">
                      View all
                    </Link>
                  </div>
                  <ul className="mt-4 space-y-1">
                    {recentRuns.map((run) => (
                      <li key={run.id}>
                        <Link
                          href={`/workflows/${run.workflow_id}`}
                          className="dashboard-recent-item block rounded-xl px-3 py-2.5"
                        >
                          <p className="truncate text-sm font-medium">{run.workflow_name}</p>
                          <p className="mt-0.5 text-[11px] text-neutral-400">{run.duration_ms}ms</p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </motion.div>
              )}

              <motion.div
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.48, duration: 0.55, ease }}
                className="workspace-panel rounded-2xl p-5"
              >
                <h2 className="text-sm font-semibold tracking-tight">System status</h2>
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between rounded-xl border border-white/50 bg-white/45 px-3 py-2.5 backdrop-blur-sm">
                    <span className="text-xs text-neutral-500">NovaFlow API</span>
                    <span
                      className={`flex items-center gap-1.5 text-xs font-semibold ${
                        healthOk === null
                          ? "text-neutral-400"
                          : healthOk
                            ? "text-emerald-600"
                            : "text-red-600"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          healthOk === null
                            ? "bg-neutral-300 animate-pulse"
                            : healthOk
                              ? "bg-emerald-500"
                              : "bg-red-500"
                        }`}
                      />
                      {healthOk === null ? "Checking…" : healthOk ? "Online" : "Offline"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-white/50 bg-white/45 px-3 py-2.5 backdrop-blur-sm">
                    <span className="text-xs text-neutral-500">Workspace</span>
                    <span className="text-xs font-semibold text-emerald-600">Ready</span>
                  </div>
                </div>
                <Link
                  href="/settings"
                  className="mt-4 inline-flex text-xs font-semibold text-neutral-700 hover:text-neutral-900"
                >
                  Open settings →
                </Link>
              </motion.div>
            </aside>
          </div>

          {!loading && !user && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, ease }}
              className="mt-12 text-center"
            >
              <div className="dashboard-panel mx-auto max-w-md rounded-2xl p-8">
                <p className="font-serif text-2xl tracking-tight">Sign in to your workspace</p>
                <p className="mt-2 text-sm text-neutral-500">
                  Access chat, knowledge bases, and published assistants.
                </p>
                <Link href="/login" className="btn-primary mt-6 inline-flex">
                  Sign in
                </Link>
              </div>
            </motion.div>
          )}
        </main>
      </div>
    </div>
  );
}
