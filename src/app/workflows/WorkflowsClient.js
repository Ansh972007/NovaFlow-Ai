"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { WorkspaceSkeletonList, WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import WorkspaceEmpty from "@/components/workspace/WorkspaceEmpty";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import TiltCard from "@/components/TiltCard";
import { getUserInfo } from "@/lib/api/auth";
import { ensureActiveWorkspace } from "@/lib/api/workspaces";
import {
  createWorkflow,
  deleteWorkflow,
  getWorkflowTemplates,
  getWorkflowsPage,
  setWorkflowStatus,
} from "@/lib/api/workflows";
import { WORKFLOW_TEMPLATES } from "@/lib/workflow/templates";

const ease = [0.16, 1, 0.3, 1];

export default function WorkflowsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [workflows, setWorkflows] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [templateId, setTemplateId] = useState("rag");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const publishedCount = workflows.filter((w) => w.status === 1).length;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [res, tpl] = await Promise.all([
        getWorkflowsPage({ limit: 50 }).catch(() => ({ data: [], total: 0 })),
        getWorkflowTemplates(),
      ]);
      setWorkflows(res?.data || []);
      setTotal(res?.total || 0);
      setTemplates(Array.isArray(tpl) && tpl.length ? tpl : WORKFLOW_TEMPLATES);
    } catch {
      setWorkflows([]);
      setTemplates(WORKFLOW_TEMPLATES);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        await ensureActiveWorkspace();
        setUser(u);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      await ensureActiveWorkspace();
      const wf = await createWorkflow({ name: name.trim(), templateId });
      if (!wf?.id) {
        throw new Error("Workflow was created but the server did not return an ID. Refresh and try again.");
      }
      setShowCreate(false);
      setName("");
      router.push(`/workflows/${wf.id}`);
    } catch (err) {
      setError(err.message || "Failed to create workflow");
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(wf) {
    setBusyId(wf.id);
    try {
      await setWorkflowStatus(wf.id, wf.status === 1 ? 0 : 1);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(wf) {
    if (!confirm(`Delete workflow "${wf.name}"?`)) return;
    setBusyId(wf.id);
    try {
      await deleteWorkflow(wf.id);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  if (!user) {
    return null;
  }

  const displayTemplates = templates.length ? templates : WORKFLOW_TEMPLATES;

  return (
    <>
      <WorkspacePageShell user={user} maxWidth="max-w-6xl">
          <WorkspaceHero
            eyebrow="Automate"
            title="Workflow"
            titleHighlight="engine"
            description="Build visual pipelines — trigger, retrieve, LLM, output — and run them on demand."
            badge={
              <span className="workspace-badge-live">
                {publishedCount} live
              </span>
            }
            actions={
              <button type="button" onClick={() => setShowCreate(true)} className="btn-primary shrink-0">
                + New workflow
              </button>
            }
          />

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              { label: "Total workflows", value: total },
              { label: "Published", value: publishedCount },
              { label: "Templates", value: displayTemplates.length },
            ].map((s, i) => (
              <WorkspaceStatCard key={s.label} label={s.label} value={s.value} index={i} />
            ))}
          </div>

          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, ease }}
            className="mt-10"
          >
            <p className="workspace-section-label mb-5">Your workflows</p>
            {loading ? (
              <WorkspaceSkeletonList count={4} height="h-20" />
            ) : workflows.length === 0 ? (
              <WorkspaceEmpty
                title="No workflows yet"
                description="Start from a template and open the visual builder."
                actionLabel="Create workflow"
                onAction={() => setShowCreate(true)}
                icon="⚡"
              />
            ) : (
              <ul className="space-y-3">
                {workflows.map((wf, i) => (
                  <motion.li
                    key={wf.id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 + i * 0.04, ease }}
                    whileHover={{ x: 4 }}
                    className="workspace-list-row flex flex-col gap-3 rounded-2xl px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-semibold">{wf.name}</p>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                            wf.status === 1 ? "bg-emerald-50 text-emerald-700" : "bg-neutral-100 text-neutral-500"
                          }`}
                        >
                          {wf.status === 1 ? "Live" : "Draft"}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-sm text-neutral-500">{wf.desc || "No description"}</p>
                    </div>
                    <div className="flex shrink-0 flex-wrap gap-2">
                      <Link href={`/workflows/${wf.id}`} className="workspace-btn-ghost">
                  Open studio
                </Link>
                      <button
                        type="button"
                        disabled={busyId === wf.id}
                        onClick={() => toggleStatus(wf)}
                        className="workspace-btn-ghost"
                      >
                        {wf.status === 1 ? "Unpublish" : "Publish"}
                      </button>
                      <button
                        type="button"
                        disabled={busyId === wf.id}
                        onClick={() => handleDelete(wf)}
                        className="workspace-btn-ghost workspace-btn-danger"
                      >
                        Delete
                      </button>
                    </div>
                  </motion.li>
                ))}
              </ul>
            )}
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, ease }}
            className="mt-10"
          >
            <p className="workspace-section-label mb-5">Starter templates</p>
            <div className="grid gap-4 md:grid-cols-3">
              {displayTemplates.map((tpl, i) => (
                <motion.div
                  key={tpl.id}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.22 + i * 0.05, ease }}
                >
                  <TiltCard>
                    <button
                      type="button"
                      onClick={() => {
                        setTemplateId(tpl.id);
                        setName(tpl.name);
                        setShowCreate(true);
                      }}
                      className="workspace-card w-full rounded-2xl p-6 text-left"
                    >
                      <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-bold uppercase text-neutral-500">
                        Template
                      </span>
                      <h3 className="mt-4 text-lg font-semibold tracking-tight">{tpl.name}</h3>
                      <p className="mt-2 text-sm text-neutral-500">{tpl.desc}</p>
                      <p className="mt-4 text-xs font-semibold text-neutral-900 opacity-60 transition-opacity group-hover:opacity-100">
                        Use template →
                      </p>
                    </button>
                  </TiltCard>
                </motion.div>
              ))}
            </div>
          </motion.section>
      </WorkspacePageShell>

      {showCreate && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4 backdrop-blur-sm"
        >
          <motion.form
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.45, ease }}
            onSubmit={handleCreate}
            className="workspace-modal w-full max-w-md rounded-2xl p-6"
          >
            <h2 className="text-lg font-semibold">New workflow</h2>
            <label className="mt-4 block text-sm font-medium">
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm"
                required
              />
            </label>
            <label className="mt-3 block text-sm font-medium">
              Template
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm"
              >
                {displayTemplates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            {error && <WorkspaceAlert type="error" className="mt-3">{error}</WorkspaceAlert>}
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setShowCreate(false)} className="workspace-btn-ghost">
                Cancel
              </button>
              <button type="submit" disabled={creating} className="btn-primary">
                {creating ? "Creating…" : "Create & open studio"}
              </button>
            </div>
          </motion.form>
        </motion.div>
      )}
    </>
  );
}
