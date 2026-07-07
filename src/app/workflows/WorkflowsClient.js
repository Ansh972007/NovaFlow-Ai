"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { WorkspaceSkeletonList } from "@/components/workspace/WorkspaceTabs";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { getUserInfo } from "@/lib/api/auth";
import {
  createWorkflow,
  deleteWorkflow,
  getWorkflowTemplates,
  getWorkflowsPage,
  setWorkflowStatus,
} from "@/lib/api/workflows";

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
        getWorkflowsPage({ limit: 50 }),
        getWorkflowTemplates().catch(() => []),
      ]);
      setWorkflows(res?.data || []);
      setTotal(res?.total || 0);
      setTemplates(Array.isArray(tpl) ? tpl : []);
    } catch {
      setWorkflows([]);
      setTemplates([]);
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
    setCreating(true);
    setError("");
    try {
      const wf = await createWorkflow({ name: name.trim(), templateId });
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

  const displayTemplates = templates.length
    ? templates
    : [
        { id: "rag", name: "RAG Q&A pipeline", desc: "Retrieve docs then answer" },
        { id: "support", name: "Support triage", desc: "Classify and draft replies" },
        { id: "research", name: "Research brief", desc: "Synthesize from sources" },
      ];

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
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08 + i * 0.05, ease }}
                className="workspace-stat rounded-2xl px-5 py-4"
              >
                <p className="text-2xl font-semibold tracking-tight">{s.value}</p>
                <p className="text-xs text-neutral-500">{s.label}</p>
              </motion.div>
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
              <div className="workspace-empty rounded-2xl p-10 text-center">
                <p className="font-medium">No workflows yet</p>
                <p className="mt-1 text-sm text-neutral-500">Start from a template and open the visual builder.</p>
                <button type="button" onClick={() => setShowCreate(true)} className="btn-primary mt-5">
                  Create workflow
                </button>
              </div>
            ) : (
              <ul className="space-y-3">
                {workflows.map((wf) => (
                  <li key={wf.id} className="workspace-list-row flex flex-col gap-3 rounded-2xl px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
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
                  </li>
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
                <motion.button
                  key={tpl.id}
                  type="button"
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.22 + i * 0.05, ease }}
                  onClick={() => {
                    setTemplateId(tpl.id);
                    setName(tpl.name);
                    setShowCreate(true);
                  }}
                  className="workspace-card rounded-2xl p-6 text-left transition-transform hover:scale-[1.01]"
                >
                  <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-bold uppercase text-neutral-500">
                    Template
                  </span>
                  <h3 className="mt-4 text-lg font-semibold tracking-tight">{tpl.name}</h3>
                  <p className="mt-2 text-sm text-neutral-500">{tpl.desc}</p>
                </motion.button>
              ))}
            </div>
          </motion.section>
      </WorkspacePageShell>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4 backdrop-blur-sm">
          <form onSubmit={handleCreate} className="workspace-modal w-full max-w-md rounded-2xl p-6">
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
          </form>
        </div>
      )}
    </>
  );
}
