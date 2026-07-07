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
import { getWorkflowsPage } from "@/lib/api/workflows";
import { testNotify, getIntegrationSettings } from "@/lib/api/integrations";
import {
  listProjects,
  createProject,
  updateProject,
  deleteProject,
} from "@/lib/api/projects";

const ease = [0.16, 1, 0.3, 1];

const STATUS_OPTIONS = ["active", "paused", "done"];

export default function ProjectsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [projects, setProjects] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [telegramChat, setTelegramChat] = useState("");
  const [emailTo, setEmailTo] = useState("");
  const [workflowPick, setWorkflowPick] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, w, integ] = await Promise.all([
        listProjects().catch(() => []),
        getWorkflowsPage({ pageSize: 50 }).catch(() => ({ data: [] })),
        getIntegrationSettings().catch(() => null),
      ]);
      setProjects(p || []);
      setWorkflows(w?.data || []);
      if (integ?.telegram?.default_chat_id && !telegramChat) {
        setTelegramChat(integ.telegram.default_chat_id);
      }
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

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError("");
    try {
      await createProject({
        name: name.trim(),
        description: description.trim(),
        integrations: {
          telegram_chat_id: telegramChat.trim(),
          email_to: emailTo.trim(),
        },
        workflow_ids: workflowPick,
      });
      setName("");
      setDescription("");
      setTelegramChat("");
      setEmailTo("");
      setWorkflowPick([]);
      await load();
    } catch (err) {
      setError(err.message || "Failed to create project");
    } finally {
      setBusy(false);
    }
  }

  async function handleStatusChange(project, status) {
    setBusy(true);
    try {
      await updateProject(project.id, { status });
      await load();
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this project?")) return;
    setBusy(true);
    try {
      await deleteProject(id);
      await load();
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleTestNotify(project) {
    const chat = project.integrations?.telegram_chat_id;
    if (!chat) {
      setError("No Telegram chat ID on this project");
      return;
    }
    setBusy(true);
    try {
      await testNotify({
        channel: "telegram",
        to: chat,
        message: `NovaFlow test from project "${project.name}"`,
      });
    } catch (err) {
      setError(err.message || "Notify test failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleWorkflow(id) {
    setWorkflowPick((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  const activeCount = projects.filter((p) => p.status === "active").length;

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />
        <main className="workspace-page-main mx-auto max-w-6xl px-4 py-10 sm:px-6">
          <WorkspaceHero
            eyebrow="Dev Projects"
            title="Map workflows to real integrations"
            description="Track Telegram, email, and workflow links per project. Use workflow templates like Telegram Q&A and daily digest from the Workflows page."
          />

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <WorkspaceStatCard label="Projects" value={projects.length} />
            <WorkspaceStatCard label="Active" value={activeCount} />
            <WorkspaceStatCard label="Workflows" value={workflows.length} />
          </div>

          {error && <WorkspaceAlert type="error" className="mt-6">{error}</WorkspaceAlert>}

          {loading ? (
            <WorkspaceLoading className="mt-10" message="Loading projects…" />
          ) : (
            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              <motion.form
                onSubmit={handleCreate}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ease }}
                className="workspace-panel rounded-[1.5rem] p-5"
              >
                <h2 className="text-lg font-semibold">New project</h2>
                <input
                  className="input-field mt-4 w-full text-sm"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Project name"
                  required
                />
                <textarea
                  className="input-field mt-3 w-full resize-none text-sm"
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Description"
                />
                <input
                  className="input-field mt-3 w-full text-sm"
                  value={telegramChat}
                  onChange={(e) => setTelegramChat(e.target.value)}
                  placeholder="Telegram chat ID"
                />
                <input
                  className="input-field mt-3 w-full text-sm"
                  value={emailTo}
                  onChange={(e) => setEmailTo(e.target.value)}
                  placeholder="Email for digests"
                />
                <p className="mt-4 text-xs font-semibold text-neutral-600">Linked workflows</p>
                <div className="mt-2 max-h-32 space-y-1 overflow-y-auto">
                  {workflows.map((wf) => (
                    <label key={wf.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={workflowPick.includes(wf.id)}
                        onChange={() => toggleWorkflow(wf.id)}
                      />
                      {wf.name}
                    </label>
                  ))}
                </div>
                <button type="submit" disabled={busy} className="btn-primary mt-4 w-full">
                  Create project
                </button>
              </motion.form>

              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05, ease }}
                className="workspace-panel rounded-[1.5rem] p-5"
              >
                <h2 className="text-lg font-semibold">Your projects</h2>
                {projects.length === 0 ? (
                  <p className="mt-4 text-sm text-neutral-500">No projects yet.</p>
                ) : (
                  <ul className="mt-4 space-y-3">
                    {projects.map((p) => (
                      <li
                        key={p.id}
                        className="rounded-xl border border-black/[0.06] bg-white/80 p-4"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-semibold">{p.name}</p>
                            <p className="mt-1 text-xs text-neutral-500">{p.description || "—"}</p>
                            <p className="mt-2 text-[11px] text-neutral-400">
                              {p.workflow_ids?.length || 0} workflows · TG:{" "}
                              {p.integrations?.telegram_chat_id || "—"}
                            </p>
                          </div>
                          <select
                            className="input-field !w-auto text-xs"
                            value={p.status}
                            onChange={(e) => handleStatusChange(p, e.target.value)}
                            disabled={busy}
                          >
                            {STATUS_OPTIONS.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Link href={`/projects/${p.id}`} className="btn-primary text-xs">
                            Open
                          </Link>
                          <button
                            type="button"
                            className="btn-secondary text-xs"
                            disabled={busy}
                            onClick={() => handleTestNotify(p)}
                          >
                            Test Telegram
                          </button>
                          <Link href="/workflows" className="btn-secondary text-xs">
                            Workflows
                          </Link>
                          <button
                            type="button"
                            className="text-xs text-red-600"
                            disabled={busy}
                            onClick={() => handleDelete(p.id)}
                          >
                            Delete
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </motion.section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
