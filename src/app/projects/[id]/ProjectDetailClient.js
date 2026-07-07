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
import WorkspaceBackLink from "@/components/workspace/WorkspaceBackLink";
import { getUserInfo } from "@/lib/api/auth";
import {
  getProject,
  updateProject,
  runProjectWorkflow,
} from "@/lib/api/projects";
import {
  testNotify,
  testEmailIntegration,
  getIntegrationHealth,
} from "@/lib/api/integrations";

const ease = [0.16, 1, 0.3, 1];

export default function ProjectDetailClient({ projectId }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [runInput, setRunInput] = useState("");
  const [runWorkflowId, setRunWorkflowId] = useState("");
  const [lastRun, setLastRun] = useState(null);
  const [health, setHealth] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, h] = await Promise.all([
        getProject(projectId),
        getIntegrationHealth().catch(() => null),
      ]);
      setProject(p);
      setHealth(h);
      if (p?.workflows?.[0]?.id) setRunWorkflowId(p.workflows[0].id);
    } catch (err) {
      setError(err.message || "Project not found");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  async function handleStatus(status) {
    setBusy(true);
    try {
      await updateProject(projectId, { status });
      await load();
      setMsg(`Status updated to ${status}`);
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRun(e) {
    e.preventDefault();
    if (!runWorkflowId || !runInput.trim()) return;
    setBusy(true);
    setError("");
    try {
      const result = await runProjectWorkflow(projectId, runWorkflowId, {
        input: runInput.trim(),
        chat_id: project?.integrations?.telegram_chat_id,
      });
      setLastRun(result);
      setMsg("Workflow run completed.");
    } catch (err) {
      setError(err.message || "Run failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleTestTelegram() {
    const chat = project?.integrations?.telegram_chat_id;
    if (!chat) {
      setError("No Telegram chat ID on this project");
      return;
    }
    setBusy(true);
    try {
      await testNotify({ channel: "telegram", to: chat, message: `Test from project "${project.name}"` });
      setMsg("Telegram test sent.");
    } catch (err) {
      setError(err.message || "Telegram test failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleTestEmail() {
    const email = project?.integrations?.email_to;
    if (!email) {
      setError("No email on this project");
      return;
    }
    setBusy(true);
    try {
      await testEmailIntegration({
        to: email,
        subject: `NovaFlow project: ${project.name}`,
        message: "Project email integration test.",
      });
      setMsg("Email test sent.");
    } catch (err) {
      setError(err.message || "Email test failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />
        <main className="workspace-page-main mx-auto max-w-6xl px-4 py-10 sm:px-6">
          <WorkspaceBackLink href="/projects" label="All projects" />

          {loading ? (
            <WorkspaceLoading className="mt-8" message="Loading project…" />
          ) : !project ? (
            <WorkspaceAlert type="error" className="mt-8">{error || "Not found"}</WorkspaceAlert>
          ) : (
            <>
              <WorkspaceHero
                eyebrow="Dev project"
                title={project.name}
                description={project.description || "No description"}
                badge={
                  <span className="workspace-badge-live capitalize">{project.status}</span>
                }
                actions={
                  <div className="flex flex-wrap gap-2">
                    {["active", "paused", "done"].map((s) => (
                      <button
                        key={s}
                        type="button"
                        disabled={busy || project.status === s}
                        onClick={() => handleStatus(s)}
                        className="workspace-btn-ghost text-xs capitalize disabled:opacity-50"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                }
              />

              {error && <WorkspaceAlert type="error" className="mt-4">{error}</WorkspaceAlert>}
              {msg && <WorkspaceAlert type="success" className="mt-4">{msg}</WorkspaceAlert>}

              <div className="mt-8 grid gap-6 lg:grid-cols-2">
                <motion.section
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ease }}
                  className="workspace-panel rounded-[1.5rem] p-5"
                >
                  <h2 className="text-lg font-semibold">Integrations</h2>
                  <dl className="mt-4 space-y-3 text-sm">
                    <div>
                      <dt className="text-xs font-semibold text-neutral-500">Telegram chat</dt>
                      <dd className="font-mono">{project.integrations?.telegram_chat_id || "—"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold text-neutral-500">Email</dt>
                      <dd>{project.integrations?.email_to || "—"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold text-neutral-500">Workspace integrations</dt>
                      <dd className="text-neutral-600">
                        TG {health?.telegram_ready ? "ready" : "off"} · Email{" "}
                        {health?.email_ready ? "ready" : "off"}
                      </dd>
                    </div>
                  </dl>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" className="btn-secondary text-xs" disabled={busy} onClick={handleTestTelegram}>
                      Test Telegram
                    </button>
                    <button type="button" className="btn-secondary text-xs" disabled={busy} onClick={handleTestEmail}>
                      Test email
                    </button>
                    <Link href="/settings" className="workspace-btn-ghost text-xs">
                      Settings
                    </Link>
                  </div>
                </motion.section>

                <motion.section
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05, ease }}
                  className="workspace-panel rounded-[1.5rem] p-5"
                >
                  <h2 className="text-lg font-semibold">Run workflow</h2>
                  <form onSubmit={handleRun} className="mt-4 space-y-3">
                    <select
                      className="input-field w-full text-sm"
                      value={runWorkflowId}
                      onChange={(e) => setRunWorkflowId(e.target.value)}
                    >
                      <option value="">Select workflow…</option>
                      {(project.workflows || []).map((wf) => (
                        <option key={wf.id} value={wf.id}>
                          {wf.name} {wf.status === 1 ? "(published)" : "(draft)"}
                        </option>
                      ))}
                    </select>
                    <textarea
                      className="input-field w-full resize-none text-sm"
                      rows={3}
                      value={runInput}
                      onChange={(e) => setRunInput(e.target.value)}
                      placeholder="Input message for workflow…"
                    />
                    <button type="submit" disabled={busy || !runWorkflowId} className="btn-primary w-full disabled:opacity-50">
                      {busy ? "Running…" : "Run with project context"}
                    </button>
                  </form>
                  {lastRun?.output && (
                    <pre className="mt-4 max-h-40 overflow-auto rounded-xl bg-neutral-50 p-3 text-xs text-neutral-700">
                      {lastRun.output}
                    </pre>
                  )}
                </motion.section>

                <motion.section
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1, ease }}
                  className="workspace-panel rounded-[1.5rem] p-5 lg:col-span-2"
                >
                  <h2 className="text-lg font-semibold">Linked workflows</h2>
                  {(project.workflows || []).length === 0 ? (
                    <p className="mt-3 text-sm text-neutral-500">No workflows linked.</p>
                  ) : (
                    <ul className="mt-4 divide-y divide-black/[0.06]">
                      {project.workflows.map((wf) => (
                        <li key={wf.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                          <div>
                            <p className="font-medium">{wf.name}</p>
                            <p className="text-xs text-neutral-500">
                              {wf.status === 1 ? "Published" : "Draft"} · {wf.desc?.slice(0, 80) || "—"}
                            </p>
                          </div>
                          <Link href={`/workflows/${wf.id}`} className="btn-secondary text-xs">
                            Open builder
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </motion.section>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
