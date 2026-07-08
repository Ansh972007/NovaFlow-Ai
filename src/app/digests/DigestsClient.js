"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { listKnowledge } from "@/lib/api/knowledge";
import {
  createWorkflow,
  createWorkflowSchedule,
  deleteWorkflowSchedule,
  listWorkspaceSchedules,
  setWorkflowStatus,
  triggerWorkflowSchedule,
  updateWorkflow,
  updateWorkflowSchedule,
} from "@/lib/api/workflows";

const ease = [0.16, 1, 0.3, 1];

const CRON_PRESETS = [
  { label: "Daily 9:00 UTC", value: "0 9 * * *" },
  { label: "Weekdays 8:00", value: "0 8 * * 1-5" },
  { label: "Every Monday 10:00", value: "0 10 * * 1" },
  { label: "Hourly", value: "0 * * * *" },
];

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function DigestsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [schedules, setSchedules] = useState([]);
  const [kbs, setKbs] = useState([]);

  const [digestName, setDigestName] = useState("Daily knowledge digest");
  const [digestCron, setDigestCron] = useState("0 9 * * *");
  const [digestChannel, setDigestChannel] = useState("email");
  const [digestTo, setDigestTo] = useState("");
  const [digestKb, setDigestKb] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rows, libraries] = await Promise.all([
        listWorkspaceSchedules().catch(() => []),
        listKnowledge({ pageSize: 100 }).catch(() => ({ data: [] })),
      ]);
      setSchedules(Array.isArray(rows) ? rows : []);
      const list = Array.isArray(libraries) ? libraries : libraries?.data || [];
      setKbs(list);
      setDigestKb((prev) => prev || (list[0]?.id ? String(list[0].id) : ""));
    } catch (err) {
      setError(err.message || "Failed to load schedules");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  async function handleToggle(row) {
    setBusy(true);
    setError("");
    try {
      await updateWorkflowSchedule(row.id, { enabled: !row.enabled });
      await load();
      setMsg(row.enabled ? "Schedule paused." : "Schedule enabled.");
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleTrigger(row) {
    setBusy(true);
    setError("");
    try {
      await triggerWorkflowSchedule(row.id);
      await load();
      setMsg(`Triggered “${row.workflow_name || row.workflow_id}”.`);
    } catch (err) {
      setError(err.message || "Trigger failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(row) {
    if (!window.confirm("Delete this schedule?")) return;
    setBusy(true);
    try {
      await deleteWorkflowSchedule(row.id);
      await load();
      setMsg("Schedule deleted.");
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateDigest(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const wf = await createWorkflow({
        name: digestName.trim() || "Daily digest",
        desc: "Scheduled digest created from Digests hub",
        templateId: "daily_digest",
      });
      const graph = wf?.graph;
      if (graph?.nodes) {
        const nodes = graph.nodes.map((n) => {
          if (n.type === "retrieve" && digestKb) {
            return { ...n, data: { ...n.data, knowledge_id: Number(digestKb) } };
          }
          if (n.type === "notify") {
            return {
              ...n,
              data: {
                ...n.data,
                channel: digestChannel,
                to: digestTo.trim() || n.data?.to || "",
                subject: n.data?.subject || "Daily digest",
                message: n.data?.message || "{{output}}",
              },
            };
          }
          return n;
        });
        await updateWorkflow({
          id: wf.id,
          name: wf.name,
          desc: wf.desc || "",
          graph: { ...graph, nodes },
        });
      }
      await setWorkflowStatus(wf.id, 1);
      await createWorkflowSchedule(wf.id, {
        cron_expression: digestCron,
        input_text: "Daily digest run",
        enabled: true,
      });
      setMsg("Digest workflow published and scheduled.");
      await load();
      router.push(`/workflows/${wf.id}`);
    } catch (err) {
      setError(err.message || "Could not create digest");
    } finally {
      setBusy(false);
    }
  }

  const enabledCount = schedules.filter((s) => s.enabled).length;
  const upcoming = schedules.filter((s) => s.enabled && s.next_run_at).length;

  if (!user || loading) {
    return (
      <>
        <AppHeader user={user} />
        <WorkspaceLiveBackground />
        <WorkspaceLoading message="Loading digests…" />
      </>
    );
  }

  return (
    <>
      <AppHeader user={user} />
      <WorkspaceLiveBackground />
      <main className="relative z-10 mx-auto max-w-6xl px-4 pb-16 pt-8 sm:px-6">
        <WorkspaceHero
          eyebrow="Automation"
          title="Digests & schedules"
          description="See every cron-backed workflow in one place — pause, run now, or spin up a knowledge digest in a click."
        />

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <WorkspaceStatCard label="Schedules" value={String(schedules.length)} />
          <WorkspaceStatCard label="Enabled" value={String(enabledCount)} />
          <WorkspaceStatCard label="Upcoming" value={String(upcoming)} />
        </div>

        {(error || msg) && (
          <div className="mt-6">
            <WorkspaceAlert tone={error ? "danger" : "success"}>{error || msg}</WorkspaceAlert>
          </div>
        )}

        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease }}
          className="mt-10 rounded-2xl border border-black/[0.06] bg-white/80 p-6 shadow-sm backdrop-blur"
        >
          <h2 className="text-lg font-semibold text-neutral-900">Create a digest</h2>
          <p className="mt-1 text-sm text-neutral-500">
            Builds from the daily digest template, publishes it, and attaches a cron schedule.
          </p>
          <form onSubmit={handleCreateDigest} className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="text-xs font-semibold text-neutral-600">Name</span>
              <input
                value={digestName}
                onChange={(e) => setDigestName(e.target.value)}
                className="input-field mt-2 w-full text-sm"
              />
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-neutral-600">Knowledge base</span>
              <select
                value={digestKb}
                onChange={(e) => setDigestKb(e.target.value)}
                className="input-field mt-2 w-full text-sm"
              >
                <option value="">None</option>
                {kbs.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name || `KB #${kb.id}`}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-neutral-600">Cron</span>
              <select
                value={digestCron}
                onChange={(e) => setDigestCron(e.target.value)}
                className="input-field mt-2 w-full text-sm"
              >
                {CRON_PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label} ({p.value})
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-neutral-600">Channel</span>
              <select
                value={digestChannel}
                onChange={(e) => setDigestChannel(e.target.value)}
                className="input-field mt-2 w-full text-sm"
              >
                <option value="email">Email</option>
                <option value="slack">Slack</option>
                <option value="discord">Discord</option>
                <option value="telegram">Telegram</option>
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-neutral-600">
                {digestChannel === "email" ? "To email" : digestChannel === "slack" ? "Webhook override (optional)" : "Chat ID"}
              </span>
              <input
                value={digestTo}
                onChange={(e) => setDigestTo(e.target.value)}
                placeholder={digestChannel === "email" ? "team@company.com" : digestChannel === "slack" ? "Uses Settings if blank" : "{{chat_id}}"}
                className="input-field mt-2 w-full text-sm"
              />
            </label>
            <div className="flex items-end sm:col-span-2">
              <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
                Create & schedule
              </button>
            </div>
          </form>
        </motion.section>

        <section className="mt-10">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-neutral-900">All schedules</h2>
            <Link href="/workflows" className="text-sm font-medium text-neutral-600 underline-offset-2 hover:underline">
              Open workflows
            </Link>
          </div>

          {schedules.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-black/10 bg-white/50 px-6 py-12 text-center text-sm text-neutral-500">
              No schedules yet. Publish a workflow and add a cron in the builder, or create a digest above.
            </div>
          ) : (
            <ul className="space-y-3">
              {schedules.map((row, i) => (
                <motion.li
                  key={row.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: i * 0.03, ease }}
                  className="flex flex-col gap-3 rounded-2xl border border-black/[0.06] bg-white/80 p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <Link
                      href={`/workflows/${row.workflow_id}`}
                      className="font-semibold text-neutral-900 hover:underline"
                    >
                      {row.workflow_name || row.workflow_id}
                    </Link>
                    <p className="mt-1 font-mono text-xs text-neutral-500">{row.cron_expression}</p>
                    <p className="mt-1 text-xs text-neutral-400">
                      Next {fmtTime(row.next_run_at)} · Last {fmtTime(row.last_run_at)}
                      {row.enabled ? "" : " · paused"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleTrigger(row)}
                      className="btn-secondary text-xs disabled:opacity-50"
                    >
                      Run now
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleToggle(row)}
                      className="btn-secondary text-xs disabled:opacity-50"
                    >
                      {row.enabled ? "Pause" : "Enable"}
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleDelete(row)}
                      className="workspace-btn-ghost workspace-btn-danger text-xs"
                    >
                      Delete
                    </button>
                  </div>
                </motion.li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
