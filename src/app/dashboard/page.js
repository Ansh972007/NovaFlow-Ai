"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import DashboardModules from "@/components/dashboard/DashboardModules";
import DashboardPulse from "@/components/dashboard/DashboardPulse";
import { getUserInfo } from "@/lib/api/auth";
import { getOnlineApps, getAssistants } from "@/lib/api/apps";
import { getAnalyticsSummary, getAnalyticsTimeseries, getAnalyticsAssistants, getAbRoutingAnalytics } from "@/lib/api/analytics";
import { listKnowledge } from "@/lib/api/knowledge";
import { getIntegrationHealth } from "@/lib/api/integrations";
import { listProjects } from "@/lib/api/projects";
import { listPipelines, getPromptDrift } from "@/lib/api/modelLab";
import { listWorkspaceSchedules } from "@/lib/api/workflows";
import { loadSessions } from "@/lib/chat/storage";
import { isSetupComplete } from "@/lib/setup/storage";

const AnalyticsCharts = dynamic(() => import("@/components/dashboard/AnalyticsCharts"), {
  ssr: false,
});

const ease = [0.16, 1, 0.3, 1];

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function buildPulseCards(workspacePulse) {
  const integrationsOn = [
    workspacePulse.integrations?.telegram_ready,
    workspacePulse.integrations?.email_ready,
    workspacePulse.integrations?.slack_ready,
    workspacePulse.integrations?.jira_ready,
    workspacePulse.integrations?.github_ready,
  ].filter(Boolean).length;

  return [
    {
      href: "/settings?tab=integrations",
      label: "Integrations",
      value: integrationsOn >= 3 ? "Ops ready" : integrationsOn > 0 ? "Partial" : "Setup needed",
      hint: `TG ${workspacePulse.integrations?.telegram_ready ? "on" : "off"} · Email ${workspacePulse.integrations?.email_ready ? "on" : "off"} · Slack ${workspacePulse.integrations?.slack_ready ? "on" : "off"}`,
      extra: `Jira ${workspacePulse.integrations?.jira_ready ? "on" : "off"} · GitHub ${workspacePulse.integrations?.github_ready ? "on" : "off"}`,
    },
    {
      href: "/credentials",
      label: "Credentials",
      value: String(workspacePulse.schedules),
      hint: `${workspacePulse.schedulesEnabled} digest schedules · vault for keys`,
    },
    {
      href: "/projects",
      label: "Projects",
      value: String(workspacePulse.projects),
      hint: "Dev integration hubs",
    },
    {
      href: "/model-lab",
      label: "Model Lab",
      value: String(workspacePulse.activeJobs),
      hint: "Active training jobs",
    },
    {
      href: "/evaluation",
      label: "Drift radar",
      value: String(workspacePulse.driftWarnings),
      hint: "Warnings + critical",
    },
  ];
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recentRuns, setRecentRuns] = useState([]);
  const [chartSeries, setChartSeries] = useState([]);
  const [topAssistants, setTopAssistants] = useState([]);
  const [abRouting, setAbRouting] = useState(null);
  const [workspacePulse, setWorkspacePulse] = useState({
    integrations: null,
    projects: 0,
    activeJobs: 0,
    driftWarnings: 0,
    schedules: 0,
    schedulesEnabled: 0,
  });
  const [stats, setStats] = useState([
    { value: "0", label: "Chat sessions", hint: "Local history" },
    { value: "0", label: "Assistants", hint: "Published & draft" },
    { value: "0", label: "Knowledge bases", hint: "Document libraries" },
    { value: "0", label: "Workflow runs", hint: "Last 7 days" },
  ]);

  const greeting = useMemo(() => getGreeting(), []);
  const pulseCards = useMemo(() => buildPulseCards(workspacePulse), [workspacePulse]);

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
          const [summary, ts, usage, ab, integ, projects, pipes, drift, schedules] = await Promise.all([
            getAnalyticsSummary(),
            getAnalyticsTimeseries(7).catch(() => null),
            getAnalyticsAssistants(7).catch(() => null),
            getAbRoutingAnalytics(30).catch(() => null),
            getIntegrationHealth().catch(() => null),
            listProjects().catch(() => []),
            listPipelines().catch(() => []),
            getPromptDrift().catch(() => null),
            listWorkspaceSchedules().catch(() => []),
          ]);
          analytics = summary;
          setRecentRuns(summary?.recent_runs || []);
          setChartSeries(ts?.series || []);
          setTopAssistants(usage?.items || []);
          setAbRouting(ab);
          const activeJobs = (pipes || []).filter(
            (p) => !["succeeded", "failed", "cancelled", "completed"].includes(p.status)
          );
          const schedRows = Array.isArray(schedules) ? schedules : [];
          setWorkspacePulse({
            integrations: integ,
            projects: (projects || []).length,
            activeJobs: activeJobs.length,
            driftWarnings: (drift?.warning_count || 0) + (drift?.critical_count || 0),
            schedules: schedRows.length,
            schedulesEnabled: schedRows.filter((s) => s.enabled).length,
          });
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
  }, []);

  return (
    <WorkspacePageShell user={user} loading={loading} loadingMessage="Loading dashboard…" maxWidth="max-w-7xl">
      <WorkspaceHero
        eyebrow="Dashboard"
        subtitle={user ? `${greeting}, ${user.user_name}` : "Welcome"}
        badge={
          <span className="workspace-badge-live">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-40" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            Workspace live
          </span>
        }
        title="Your AI"
        titleHighlight="command center"
        description="Chat, knowledge, and assistants in one place — pick up where you left off or launch something new."
        actions={
          user ? (
            <>
              <Link href="/chat" className="group btn-primary inline-flex">
                Open Chat
                <span className="transition-transform group-hover:translate-x-1">→</span>
              </Link>
              <Link href="/projects?tab=assistants" className="btn-secondary">
                Manage apps
              </Link>
            </>
          ) : null
        }
      >
        {user && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat, i) => (
              <WorkspaceStatCard key={stat.label} label={stat.label} value={stat.value} hint={stat.hint} index={i} />
            ))}
          </div>
        )}
      </WorkspaceHero>

      {user && (
        <div className="mt-8 space-y-10">
          <DashboardModules />

          <div>
            <p className="workspace-section-label mb-3">Live pulse</p>
            <DashboardPulse cards={pulseCards} />
          </div>

          {recentRuns.length > 0 && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28, ease }}
            >
              <div className="mb-3 flex items-center justify-between">
                <p className="workspace-section-label">Recent workflow runs</p>
                <Link href="/workflows" className="text-xs font-medium text-neutral-500 hover:text-neutral-900">
                  View all →
                </Link>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {recentRuns.slice(0, 3).map((run) => (
                  <Link
                    key={run.id}
                    href={`/workflows/${run.workflow_id}`}
                    className="workspace-list-row block rounded-2xl px-4 py-3"
                  >
                    <p className="truncate text-sm font-semibold">{run.workflow_name}</p>
                    <p className="mt-0.5 text-xs text-neutral-500">{run.duration_ms}ms</p>
                  </Link>
                ))}
              </div>
            </motion.section>
          )}

          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.32, ease }}
          >
            <p className="workspace-section-label mb-4">Analytics</p>
            <AnalyticsCharts series={chartSeries} assistants={topAssistants} abRouting={abRouting} />
          </motion.section>
        </div>
      )}

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
    </WorkspacePageShell>
  );
}
