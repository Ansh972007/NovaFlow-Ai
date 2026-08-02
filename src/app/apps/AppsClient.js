"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { AppsIcon, BotIcon } from "@/components/workspace/WorkspaceIcons";
import { getUserInfo } from "@/lib/api/auth";
import {
  createAssistant,
  deleteAssistant,
  getAssistantsPage,
  setAssistantStatus,
} from "@/lib/api/apps";
import { PROMPT_TEMPLATES } from "@/lib/prompts/templates";

const ease = [0.16, 1, 0.3, 1];

const DEFAULT_PROMPT = PROMPT_TEMPLATES.find((t) => t.id === "github_pr")?.prompt
  || "You are a helpful NovaFlow AI assistant. Answer clearly, be concise, and ask follow-up questions when the user's request is ambiguous.";

export default function AppsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [apps, setApps] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const onlineCount = apps.filter((a) => a.status === 1).length;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getAssistantsPage({ limit: 50 });
      setApps(res?.data || []);
      setTotal(res?.total || 0);
    } catch {
      setApps([]);
      setTotal(0);
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
    if (!name.trim() || prompt.trim().length < 20) return;
    setCreating(true);
    setError("");
    try {
      await createAssistant({ name: name.trim(), prompt: prompt.trim(), logo: "" });
      setShowCreate(false);
      setName("");
      setPrompt(DEFAULT_PROMPT);
      await load();
    } catch (err) {
      setError(err.message || "Failed to create assistant");
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(app) {
    setBusyId(app.id);
    try {
      const next = app.status === 1 ? 0 : 1;
      await setAssistantStatus(app.id, next);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(app) {
    if (!window.confirm(`Delete "${app.name}"? This cannot be undone.`)) return;
    setBusyId(app.id);
    try {
      await deleteAssistant(app.id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  if (!user) {
    return null;
  }

  return (
    <>
    <WorkspacePageShell user={user} maxWidth="max-w-5xl">
          <WorkspaceHero
            eyebrow="Workspace"
            title="AI"
            titleHighlight="assistants"
            description="Create, publish, and manage assistants your team can use in Chat."
            badge={<span className="workspace-badge-live">{onlineCount} online</span>}
            actions={
              <button type="button" onClick={() => setShowCreate(true)} className="btn-primary shrink-0">
                + New assistant
              </button>
            }
          >
            {!loading && total > 0 && (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <div className="workspace-stat rounded-2xl p-4">
                  <p className="text-2xl font-semibold tabular-nums">{total}</p>
                  <p className="mt-1 text-xs text-neutral-500">Total assistants</p>
                </div>
                <div className="workspace-stat rounded-2xl p-4">
                  <p className="text-2xl font-semibold tabular-nums text-emerald-600">{onlineCount}</p>
                  <p className="mt-1 text-xs text-neutral-500">Published</p>
                </div>
                <div className="workspace-stat col-span-2 rounded-2xl p-4 sm:col-span-1">
                  <p className="text-2xl font-semibold tabular-nums">{total - onlineCount}</p>
                  <p className="mt-1 text-xs text-neutral-500">Draft / offline</p>
                </div>
              </div>
            )}
          </WorkspaceHero>

          {error && (
            <WorkspaceAlert type="error" className="mt-6">{error}</WorkspaceAlert>
          )}

          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, ease }}
            className="mt-10"
          >
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="workspace-panel h-24 animate-pulse rounded-2xl" />
                ))}
              </div>
            ) : apps.length === 0 ? (
              <div className="workspace-empty rounded-[1.75rem] p-12 text-center sm:p-16">
                <div className="workspace-icon-tile mx-auto h-14 w-14">
                  <BotIcon className="h-6 w-6" />
                </div>
                <p className="mt-6 text-xl font-semibold tracking-tight">No assistants yet</p>
                <p className="mx-auto mt-2 max-w-sm text-sm text-neutral-500">
                  Create your first assistant, publish it, and start chatting instantly.
                </p>
                <button type="button" onClick={() => setShowCreate(true)} className="btn-primary mt-8">
                  Create assistant
                </button>
              </div>
            ) : (
              <ul className="space-y-3">
                {apps.map((app, i) => (
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
                          <h2 className="truncate text-lg font-semibold tracking-tight">{app.name}</h2>
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
                        <p className="mt-1.5 text-[11px] text-neutral-400">
                          Updated {app.update_time ? new Date(app.update_time).toLocaleDateString() : "—"}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-wrap gap-2 sm:pl-4">
                      <Link href={`/apps/${app.id}`} className="workspace-btn-ghost">
                        Configure
                      </Link>
                      {app.status === 1 && (
                        <Link href={`/chat?app=${app.id}`} className="workspace-btn-ghost">
                          Open chat
                        </Link>
                      )}
                      <button
                        type="button"
                        disabled={busyId === app.id}
                        onClick={() => toggleStatus(app)}
                        className="workspace-btn-ghost disabled:opacity-50"
                      >
                        {app.status === 1 ? "Unpublish" : "Publish"}
                      </button>
                      <button
                        type="button"
                        disabled={busyId === app.id}
                        onClick={() => handleDelete(app)}
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
    </WorkspacePageShell>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4 backdrop-blur-md">
          <motion.form
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            onSubmit={handleCreate}
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
                value={name}
                onChange={(e) => setName(e.target.value)}
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
                    onClick={() => setPrompt(t.prompt)}
                    className="rounded-full border border-neutral-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-neutral-700 hover:bg-neutral-50"
                    title={t.description}
                  >
                    {t.icon} {t.name}
                  </button>
                ))}
              </div>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={5}
                className="input-field mt-2 w-full resize-none"
                required
                minLength={20}
              />
            </label>

            <div className="mt-7 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="workspace-btn-ghost"
              >
                Cancel
              </button>
              <button type="submit" disabled={creating} className="btn-primary disabled:opacity-50">
                {creating ? "Creating…" : "Create"}
              </button>
            </div>
          </motion.form>
        </div>
      )}
    </>
  );
}
