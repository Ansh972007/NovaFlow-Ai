"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { AppsIcon, BotIcon } from "@/components/workspace/WorkspaceIcons";
import { getUserInfo } from "@/lib/api/auth";
import { getWorkflowsPage } from "@/lib/api/workflows";
import { testNotify, getIntegrationSettings } from "@/lib/api/integrations";
import {
  listProjects,
  createProject,
  updateProject,
  deleteProject,
} from "@/lib/api/projects";
import {
  createAssistant,
  deleteAssistant,
  getAssistantsPage,
  setAssistantStatus,
} from "@/lib/api/apps";
import { PROMPT_TEMPLATES } from "@/lib/prompts/templates";

const ease = [0.16, 1, 0.3, 1];
const STATUS_OPTIONS = ["active", "paused", "done"];
const DEFAULT_PROMPT =
  PROMPT_TEMPLATES.find((t) => t.id === "github_pr")?.prompt ||
  "You are a helpful NovaFlow AI assistant. Answer clearly, be concise, and ask follow-up questions when the user's request is ambiguous.";

export default function ProjectsClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") === "assistants" ? "assistants" : "hub";

  const [user, setUser] = useState(null);
  const [tab, setTab] = useState(initialTab);
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

  const [assistants, setAssistants] = useState([]);
  const [assistantTotal, setAssistantTotal] = useState(0);
  const [showCreateAssistant, setShowCreateAssistant] = useState(false);
  const [assistantName, setAssistantName] = useState("");
  const [assistantPrompt, setAssistantPrompt] = useState(DEFAULT_PROMPT);
  const [creatingAssistant, setCreatingAssistant] = useState(false);
  const [busyAssistantId, setBusyAssistantId] = useState(null);

  const onlineCount = useMemo(
    () => assistants.filter((a) => a.status === 1).length,
    [assistants]
  );
  const activeCount = projects.filter((p) => p.status === "active").length;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, w, integ, a] = await Promise.all([
        listProjects().catch(() => []),
        getWorkflowsPage({ pageSize: 50 }).catch(() => ({ data: [] })),
        getIntegrationSettings().catch(() => null),
        getAssistantsPage({ limit: 50 }).catch(() => ({ data: [], total: 0 })),
      ]);
      setProjects(p || []);
      setWorkflows(w?.data || []);
      setAssistants(a?.data || []);
      setAssistantTotal(a?.total || 0);
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

  useEffect(() => {
    const next = searchParams.get("tab") === "assistants" ? "assistants" : "hub";
    setTab(next);
  }, [searchParams]);

  function switchTab(next) {
    setTab(next);
    setError("");
    const q = next === "assistants" ? "?tab=assistants" : "";
    router.replace(`/projects${q}`);
  }

  async function handleCreateProject(e) {
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

  async function handleDeleteProject(id) {
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

  async function handleCreateAssistant(e) {
    e.preventDefault();
    if (!assistantName.trim() || assistantPrompt.trim().length < 20) return;
    setCreatingAssistant(true);
    setError("");
    try {
      await createAssistant({
        name: assistantName.trim(),
        prompt: assistantPrompt.trim(),
        logo: "",
      });
      setShowCreateAssistant(false);
      setAssistantName("");
      setAssistantPrompt(DEFAULT_PROMPT);
      await load();
    } catch (err) {
      setError(err.message || "Failed to create assistant");
    } finally {
      setCreatingAssistant(false);
    }
  }

  async function toggleAssistantStatus(app) {
    setBusyAssistantId(app.id);
    try {
      await setAssistantStatus(app.id, app.status === 1 ? 0 : 1);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAssistantId(null);
    }
  }

  async function handleDeleteAssistant(app) {
    if (!window.confirm(`Delete "${app.name}"? This cannot be undone.`)) return;
    setBusyAssistantId(app.id);
    try {
      await deleteAssistant(app.id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyAssistantId(null);
    }
  }

  if (!user) return null;

  return (
    <>
      <div className="relative min-h-screen overflow-hidden">
        <WorkspaceLiveBackground />
        <div className="relative z-10">
          <AppHeader user={user} />
          <main className="workspace-page-main mx-auto max-w-6xl px-4 py-10 sm:px-6">
            <WorkspaceHero
              eyebrow="Projects"
              title="Projects & assistants"
              description="One place to manage integration hubs, workflows, and chat assistants your team uses in Build."
              badge={
                <span className="workspace-badge-live">
                  {onlineCount} assistants online
                </span>
              }
              actions={
                tab === "assistants" ? (
                  <button
                    type="button"
                    onClick={() => setShowCreateAssistant(true)}
                    className="btn-primary shrink-0"
                  >
                    + New assistant
                  </button>
                ) : null
              }
            />

            <div className="mt-6 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => switchTab("hub")}
                className={`rounded-full px-4 py-2 text-xs font-semibold transition-colors ${
                  tab === "hub"
                    ? "bg-neutral-900 text-white"
                    : "border border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50"
                }`}
              >
                Project hub
              </button>
              <button
                type="button"
                onClick={() => switchTab("assistants")}
                className={`rounded-full px-4 py-2 text-xs font-semibold transition-colors ${
                  tab === "assistants"
                    ? "bg-neutral-900 text-white"
                    : "border border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50"
                }`}
              >
                Assistants
              </button>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <WorkspaceStatCard label="Projects" value={projects.length} />
              <WorkspaceStatCard label="Active projects" value={activeCount} />
              <WorkspaceStatCard
                label={tab === "assistants" ? "Assistants" : "Workflows"}
                value={tab === "assistants" ? assistantTotal : workflows.length}
              />
            </div>

            {error && <WorkspaceAlert type="error" className="mt-6">{error}</WorkspaceAlert>}

            {loading ? (
              <WorkspaceLoading className="mt-10" message="Loading projects…" />
            ) : tab === "hub" ? (
              <div className="mt-8 grid gap-6 lg:grid-cols-2">
                <motion.form
                  onSubmit={handleCreateProject}
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
                              onClick={() => handleDeleteProject(p.id)}
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
            ) : (
              <motion.section
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, ease }}
                className="mt-8"
              >
                {assistants.length === 0 ? (
                  <div className="workspace-empty rounded-[1.75rem] p-12 text-center sm:p-16">
                    <div className="workspace-icon-tile mx-auto h-14 w-14">
                      <BotIcon className="h-6 w-6" />
                    </div>
                    <p className="mt-6 text-xl font-semibold tracking-tight">No assistants yet</p>
                    <p className="mx-auto mt-2 max-w-sm text-sm text-neutral-500">
                      Create an assistant, publish it, and use it in Build chat.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowCreateAssistant(true)}
                      className="btn-primary mt-8"
                    >
                      Create assistant
                    </button>
                  </div>
                ) : (
                  <ul className="space-y-3">
                    {assistants.map((app, i) => (
                      <motion.li
                        key={app.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.04, ease }}
                        className="workspace-list-row flex flex-col gap-4 rounded-2xl p-5 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex min-w-0 items-start gap-4">
                          <div className="workspace-icon-tile h-11 w-11 shrink-0">
                            <AppsIcon className="h-5 w-5" />
                          </div>
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <h2 className="truncate text-lg font-semibold tracking-tight">
                                {app.name}
                              </h2>
                              <span
                                className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase ${
                                  app.status === 1
                                    ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60"
                                    : "bg-neutral-100 text-neutral-500 ring-1 ring-neutral-200/60"
                                }`}
                              >
                                {app.status === 1 ? "Online" : "Offline"}
                              </span>
                            </div>
                            {app.desc && (
                              <p className="mt-1 line-clamp-2 text-sm text-neutral-500">{app.desc}</p>
                            )}
                          </div>
                        </div>
                        <div className="flex shrink-0 flex-wrap gap-2 sm:pl-4">
                          <Link
                            href={`/projects/assistants/${app.id}`}
                            className="workspace-btn-ghost"
                          >
                            Configure
                          </Link>
                          {app.status === 1 && (
                            <Link href={`/chat?app=${app.id}`} className="workspace-btn-ghost">
                              Open chat
                            </Link>
                          )}
                          <button
                            type="button"
                            disabled={busyAssistantId === app.id}
                            onClick={() => toggleAssistantStatus(app)}
                            className="workspace-btn-ghost disabled:opacity-50"
                          >
                            {app.status === 1 ? "Unpublish" : "Publish"}
                          </button>
                          <button
                            type="button"
                            disabled={busyAssistantId === app.id}
                            onClick={() => handleDeleteAssistant(app)}
                            className="workspace-btn-ghost workspace-btn-danger disabled:opacity-50"
                          >
                            Delete
                          </button>
                        </div>
                      </motion.li>
                    ))}
                  </ul>
                )}
              </motion.section>
            )}
          </main>
        </div>
      </div>

      {showCreateAssistant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4 backdrop-blur-md">
          <motion.form
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            onSubmit={handleCreateAssistant}
            className="workspace-modal w-full max-w-md rounded-[1.5rem] p-7 sm:p-8"
          >
            <div className="flex items-start gap-4">
              <div className="workspace-icon-tile h-12 w-12 shrink-0">
                <BotIcon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-serif text-2xl tracking-tight">New assistant</h2>
                <p className="mt-1 text-sm text-neutral-500">Prompt must be at least 20 characters.</p>
              </div>
            </div>

            <label className="mt-7 block text-sm font-medium">
              Name
              <input
                value={assistantName}
                onChange={(e) => setAssistantName(e.target.value)}
                className="input-field mt-1.5 w-full"
                placeholder="My Assistant"
                required
              />
            </label>
            <label className="mt-4 block text-sm font-medium">
              System prompt
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {PROMPT_TEMPLATES.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setAssistantPrompt(t.prompt)}
                    className="rounded-full border border-neutral-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-neutral-700 hover:bg-neutral-50"
                    title={t.description}
                  >
                    {t.icon} {t.name}
                  </button>
                ))}
              </div>
              <textarea
                value={assistantPrompt}
                onChange={(e) => setAssistantPrompt(e.target.value)}
                rows={5}
                className="input-field mt-2 w-full resize-none"
                required
                minLength={20}
              />
            </label>

            <div className="mt-7 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowCreateAssistant(false)}
                className="workspace-btn-ghost"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creatingAssistant}
                className="btn-primary disabled:opacity-50"
              >
                {creatingAssistant ? "Creating…" : "Create"}
              </button>
            </div>
          </motion.form>
        </div>
      )}
    </>
  );
}
