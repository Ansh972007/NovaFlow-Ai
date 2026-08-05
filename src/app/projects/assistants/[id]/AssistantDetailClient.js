"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import WorkspaceBackLink from "@/components/workspace/WorkspaceBackLink";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { BotIcon, KnowledgeIcon } from "@/components/workspace/WorkspaceIcons";
import { getUserInfo } from "@/lib/api/auth";
import {
  deleteAssistant,
  getAssistantInfo,
  setAssistantKnowledge,
  setAssistantStatus,
  updateAssistant,
} from "@/lib/api/apps";
import { getAssistantAnalytics } from "@/lib/api/analytics";
import { listKnowledge } from "@/lib/api/knowledge";
import AssistantAnalytics from "@/components/apps/AssistantAnalytics";

const ease = [0.16, 1, 0.3, 1];

export default function AssistantDetailClient({ assistantId }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState(0);
  const [linkedIds, setLinkedIds] = useState([]);
  const [libraries, setLibraries] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [info, kbRes, analyticsRes] = await Promise.all([
        getAssistantInfo(assistantId),
        listKnowledge({ pageSize: 100 }),
        getAssistantAnalytics(assistantId).catch(() => null),
      ]);
      setName(info?.name || "");
      setDesc(info?.desc || info?.description || "");
      setPrompt(info?.prompt || "");
      setStatus(info?.status ?? 0);
      setLinkedIds(info?.knowledge_ids || info?.knowledge_list?.map((k) => k.id) || []);
      setLibraries(kbRes?.data || []);
      setAnalytics(analyticsRes);
    } catch (err) {
      setError(err.message || "Failed to load assistant");
    } finally {
      setLoading(false);
    }
  }, [assistantId]);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  function toggleLibrary(id) {
    setLinkedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    if (prompt.trim().length < 20) {
      setError("Prompt must be at least 20 characters");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await updateAssistant({
        id: assistantId,
        name: name.trim(),
        desc: desc.trim(),
        prompt: prompt.trim(),
      });
      await setAssistantKnowledge(assistantId, linkedIds);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleTogglePublish() {
    setSaving(true);
    try {
      const next = status === 1 ? 0 : 1;
      await setAssistantStatus(assistantId, next);
      setStatus(next);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await deleteAssistant(assistantId);
      router.push("/projects?tab=assistants");
    } catch (err) {
      setError(err.message);
    }
  }

  if (!user) {
    return <WorkspaceLoading message="Loading assistantâ€¦" />;
  }

  const readOnly = user.role === "viewer";

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground active={saving} />
      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="workspace-page-main mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-12">
          <WorkspaceBackLink href="/projects?tab=assistants">All assistants</WorkspaceBackLink>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
            className="workspace-hero rounded-[1.75rem] p-7 sm:p-9"
          >
            <div className="workspace-hero-glow pointer-events-none absolute inset-0" aria-hidden />
            <div className="relative flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-4">
                <div className="workspace-icon-tile h-14 w-14 shrink-0">
                  <BotIcon className="h-6 w-6" />
                </div>
                <div>
                  <p className="workspace-section-label">Assistant studio</p>
                  <h1 className="mt-1 font-serif text-3xl tracking-tight sm:text-4xl">
                    {loading ? "Loadingâ€¦" : name || "Assistant"}
                  </h1>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${
                        status === 1
                          ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60"
                          : "bg-neutral-100 text-neutral-500 ring-1 ring-neutral-200/60"
                      }`}
                    >
                      {status === 1 ? "Published" : "Draft"}
                    </span>
                    {linkedIds.length > 0 && (
                      <span className="rounded-full bg-white/70 px-2.5 py-0.5 text-[10px] font-semibold text-neutral-600 ring-1 ring-black/5">
                        {linkedIds.length} knowledge {linkedIds.length === 1 ? "base" : "bases"} linked
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {status === 1 && (
                  <Link href={`/chat?app=${assistantId}`} className="workspace-btn-ghost">
                    Open chat
                  </Link>
                )}
                {!readOnly && (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={handleTogglePublish}
                    className="workspace-btn-ghost disabled:opacity-50"
                  >
                    {status === 1 ? "Unpublish" : "Publish"}
                  </button>
                )}
              </div>
            </div>
          </motion.div>

          {error && <WorkspaceAlert type="error" className="mt-4">{error}</WorkspaceAlert>}

          {readOnly && (
            <WorkspaceAlert type="warn" className="mt-4">
              Viewer access â€” you can inspect this assistant but cannot edit it.
            </WorkspaceAlert>
          )}

          {saved && (
            <WorkspaceAlert type="success" className="mt-4">
              Changes saved â€” RAG links active in chat.
            </WorkspaceAlert>
          )}

          <form onSubmit={handleSave} className="mt-8 space-y-6">
            <fieldset disabled={readOnly} className="space-y-6 disabled:opacity-80">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
            >
              <h2 className="text-lg font-semibold tracking-tight">Identity</h2>
              <p className="mt-1 text-sm text-neutral-500">Name and description shown in chat.</p>
              <div className="mt-5 space-y-4">
                <label className="block text-sm font-medium">
                  Name
                  <input
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      setSaved(false);
                    }}
                    className="input-field mt-1.5 w-full"
                    required
                  />
                </label>
                <label className="block text-sm font-medium">
                  Description
                  <textarea
                    value={desc}
                    onChange={(e) => {
                      setDesc(e.target.value);
                      setSaved(false);
                    }}
                    rows={2}
                    className="input-field mt-1.5 w-full resize-none"
                    placeholder="Optional welcome message or summary"
                  />
                </label>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
            >
              <h2 className="text-lg font-semibold tracking-tight">System prompt</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Core instructions for this assistant. Minimum 20 characters.
              </p>
              <textarea
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  setSaved(false);
                }}
                rows={8}
                className="input-field mt-5 w-full resize-y font-mono text-[13px] leading-relaxed"
                required
                minLength={20}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.16, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
            >
              <div className="flex items-start gap-4">
                <div className="workspace-icon-tile h-11 w-11 shrink-0">
                  <KnowledgeIcon className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-semibold tracking-tight">Knowledge (RAG)</h2>
                  <p className="mt-1 text-sm text-neutral-500">
                    Link document libraries. Chat will retrieve relevant chunks automatically.
                  </p>
                </div>
              </div>

              {libraries.length === 0 ? (
                <div className="workspace-empty mt-5 rounded-xl p-6 text-center text-sm text-neutral-500">
                  No libraries yet.{" "}
                  <Link href="/knowledge" className="font-semibold text-neutral-900 hover:underline">
                    Create one â†’
                  </Link>
                </div>
              ) : (
                <ul className="mt-5 space-y-2">
                  {libraries.map((kb) => {
                    const checked = linkedIds.includes(kb.id);
                    return (
                      <li key={kb.id}>
                        <button
                          type="button"
                          onClick={() => toggleLibrary(kb.id)}
                          className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
                            checked
                              ? "border-neutral-900/20 bg-white/90 shadow-sm"
                              : "border-white/60 bg-white/50 hover:bg-white/70"
                          }`}
                        >
                          <span
                            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border ${
                              checked
                                ? "border-neutral-900 bg-neutral-900 text-white"
                                : "border-neutral-300 bg-white"
                            }`}
                          >
                            {checked && (
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                <path d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block font-medium text-neutral-900">{kb.name}</span>
                            {kb.description && (
                              <span className="block truncate text-xs text-neutral-500">{kb.description}</span>
                            )}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </motion.div>
            </fieldset>

            <AssistantAnalytics analytics={analytics} />

            {!readOnly && (
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <button
                type="button"
                onClick={handleDelete}
                className="workspace-btn-ghost workspace-btn-danger"
              >
                Delete assistant
              </button>
              <button type="submit" disabled={saving || loading} className="btn-primary disabled:opacity-50">
                {saving ? "Savingâ€¦" : "Save changes"}
              </button>
            </div>
            )}
          </form>
        </main>
      </div>
    </div>
  );
}
