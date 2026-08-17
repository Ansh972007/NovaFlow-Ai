"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState, Suspense } from "react";
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
import { setWorkflowPublic } from "@/lib/api/marketplace";
import { WORKFLOW_TEMPLATES } from "@/lib/workflow/templates";
import DigestsClient from "@/app/digests/DigestsClient";

const ease = [0.16, 1, 0.3, 1];

function WorkflowsClientInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = searchParams?.get("tab") === "digests" ? "digests" : "workflows";
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
  const [loadError, setLoadError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [templateBusyId, setTemplateBusyId] = useState(null);

  const publishedCount = workflows.filter((w) => w.status === 1).length;

  const starterTemplates = (templates || WORKFLOW_TEMPLATES).slice(0, 6);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [res, tpl] = await Promise.all([
        getWorkflowsPage({ limit: 50 }),
        getWorkflowTemplates().catch(() => WORKFLOW_TEMPLATES),
      ]);
      setWorkflows(res?.data || []);
      setTotal(res?.total || 0);
      setTemplates(Array.isArray(tpl) && tpl.length ? tpl : WORKFLOW_TEMPLATES);
    } catch (err) {
      setWorkflows([]);
      setTotal(0);
      setLoadError(err.message || "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        try {
          await ensureActiveWorkspace();
        } catch (err) {
          console.warn("Workspace setup:", err?.message);
        }
        setUser(u);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (tab === "workflows" && user) load();
  }, [load, tab, user]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      await ensureActiveWorkspace();
      const wf = await createWorkflow({ name: name.trim(), templateId });
      router.push(`/workflows/${wf.id}`);
    } catch (err) {
      setError(err.message || "Failed to create workflow");
    } finally {
      setCreating(false);
    }
  }

  async function handleTemplateLaunch(tpl) {
    if (templateBusyId) return;
    setTemplateBusyId(tpl.id);
    setError("");
    try {
      await ensureActiveWorkspace();
      const wf = await createWorkflow({ name: tpl.name, templateId: tpl.id });
      router.push(`/workflows/${wf.id}`);
    } catch (err) {
      setError(err.message || "Failed to launch template");
    } finally {
      setTemplateBusyId(null);
    }
  }

  if (tab === "digests") {
    return (
      <div>
        <div className="mb-4 flex flex-wrap gap-2 px-1">
          <Link
            href="/workflows"
            className="rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700"
          >
            Workflows
          </Link>
          <span className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white">Digests</span>
          <Link
            href="/credentials"
            className="rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700"
          >
            Credentials vault
          </Link>
        </div>
        <DigestsClient />
      </div>
    );
  }

  return (
    <WorkspacePageShell user={user} loading={!user || loading} loadingMessage="Loading workflows…">
      <WorkspaceHero
        eyebrow="Workflows"
        title="Automations & digests"
        description="Build visual pipelines and schedule digests. Delivery secrets live in Credentials."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/workflows?tab=digests" className="btn-secondary !py-2.5 !text-sm">
              Digests studio
            </Link>
            <button type="button" className="btn-primary !py-2.5 !text-sm" onClick={() => setShowCreate(true)}>
              New workflow
            </button>
          </div>
        }
      />

      <div className="mb-6 flex flex-wrap gap-2">
        <span className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white">Workflows</span>
        <Link
          href="/workflows?tab=digests"
          className="rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700"
        >
          Digests
        </Link>
      </div>

      {loadError ? (
        <WorkspaceAlert type="error" className="mb-4">{loadError}</WorkspaceAlert>
      ) : null}
      {error ? (
        <WorkspaceAlert type="error" className="mb-4">{error}</WorkspaceAlert>
      ) : null}

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <WorkspaceStatCard label="Total" value={total || workflows.length} />
        <WorkspaceStatCard label="Published" value={publishedCount} />
        <WorkspaceStatCard label="Drafts" value={(workflows.length || 0) - publishedCount} />
      </div>

      {showCreate ? (
        <form onSubmit={handleCreate} className="mb-6 space-y-4 rounded-2xl border border-indigo-100 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-neutral-900">Create New Workflow</h3>
          <div>
            <label className="mb-1 block text-xs font-semibold text-neutral-600">Workflow Name</label>
            <input
              className="w-full rounded-xl border border-neutral-200 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              placeholder="e.g. Daily Support Digest or Multi-Subject Email Sender"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-neutral-600">Select Architecture Template</label>
            <select
              className="w-full rounded-xl border border-neutral-200 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
            >
              {(templates || []).map((t) => (
                <option key={t.id || t.template_id} value={t.id || t.template_id}>
                  {t.name || t.id} — {t.desc || ""}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="submit" className="btn-primary !px-5 !py-2.5 !text-sm" disabled={creating}>
              {creating ? "Creating..." : "Launch Workflow"}
            </button>
            <button type="button" className="btn-secondary !px-5 !py-2.5 !text-sm" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      <div className="mb-8 space-y-3">
        <div>
          <h3 className="text-base font-semibold text-neutral-900">Starter Workflow Templates</h3>
          <p className="text-xs text-neutral-500">Launch pre-configured multi-node workflows with 1 click.</p>
        </div>
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {starterTemplates.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              disabled={templateBusyId === tpl.id}
              className="group relative flex flex-col justify-between rounded-2xl border border-neutral-200/80 bg-white p-4 text-left transition-all hover:border-indigo-300 hover:shadow-md disabled:opacity-60"
              onClick={() => handleTemplateLaunch(tpl)}
            >
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-600">
                    Template
                  </span>
                  <span className="text-[11px] font-medium text-indigo-600 group-hover:translate-x-0.5 transition-transform">
                    {templateBusyId === tpl.id ? "Launching…" : "Use Template ➔"}
                  </span>
                </div>
                <h4 className="text-sm font-semibold text-neutral-900">{tpl.name}</h4>
                <p className="mt-1 line-clamp-2 text-xs text-neutral-500">{tpl.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <WorkspaceSkeletonList />
      ) : workflows.length === 0 && !loadError ? (
        <WorkspaceEmpty title="No workflows yet" description="Create one from a template to get started." />
      ) : workflows.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {workflows.map((wf, i) => (
            <motion.div
              key={wf.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03, ease }}
            >
              <TiltCard className="rounded-2xl border border-neutral-200 bg-white p-5">
                  <Link href={`/workflows/${wf.id}`} className="block">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold text-neutral-900">{wf.name}</p>
                      {wf.is_public === 1 && (
                        <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
                          Marketplace
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-neutral-500">{wf.status === 1 ? "Published" : "Draft"}</p>
                  </Link>
                  <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-neutral-100 pt-3">
                    <button
                      type="button"
                      className="rounded-lg bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-200 transition"
                      disabled={busyId === wf.id}
                      onClick={async () => {
                        setBusyId(wf.id);
                        setError("");
                        try {
                          await setWorkflowStatus(wf.id, wf.status === 1 ? 0 : 1);
                          await load();
                        } catch (err) {
                          setError(err.message || "Status update failed");
                        } finally {
                          setBusyId(null);
                        }
                      }}
                    >
                      {wf.status === 1 ? "Unpublish" : "Publish"}
                    </button>
                    <button
                      type="button"
                      className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                        wf.is_public === 1
                          ? "bg-violet-50 text-violet-700 hover:bg-violet-100"
                          : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                      }`}
                      disabled={busyId === wf.id}
                      onClick={async () => {
                        setBusyId(wf.id);
                        setError("");
                        try {
                          const next = wf.is_public !== 1;
                          await setWorkflowPublic(wf.id, next);
                          await load();
                        } catch (err) {
                          setError(err.message || "Marketplace share failed");
                        } finally {
                          setBusyId(null);
                        }
                      }}
                    >
                      {wf.is_public === 1 ? "Unshare from Market" : "Share to Market"}
                    </button>
                    <button
                      type="button"
                      className="ml-auto rounded-lg px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50 transition"
                      disabled={busyId === wf.id}
                      onClick={async () => {
                        if (!window.confirm("Delete workflow?")) return;
                        setBusyId(wf.id);
                        setError("");
                        try {
                          await deleteWorkflow(wf.id);
                          await load();
                        } catch (err) {
                          setError(err.message || "Delete failed");
                        } finally {
                          setBusyId(null);
                        }
                      }}
                    >
                      Delete
                    </button>
                  </div>
              </TiltCard>
            </motion.div>
          ))}
        </div>
      ) : null}
    </WorkspacePageShell>
  );
}

export default function WorkflowsClient() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-neutral-500">Loading workflows…</div>}>
      <WorkflowsClientInner />
    </Suspense>
  );
}
