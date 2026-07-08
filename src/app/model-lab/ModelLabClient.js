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
import { listEvalSuites } from "@/lib/api/evaluation";
import { listFineTuneDatasets } from "@/lib/api/finetune";
import {
  createDatasetFromKnowledge,
  trainAndEval,
  listPipelines,
  refreshPipelineJob,
  deployPipelineAssistant,
} from "@/lib/api/modelLab";

const ease = [0.16, 1, 0.3, 1];

export default function ModelLabClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [knowledge, setKnowledge] = useState([]);
  const [suites, setSuites] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [pipelines, setPipelines] = useState([]);
  const [selectedKb, setSelectedKb] = useState([]);
  const [datasetName, setDatasetName] = useState("Knowledge training set");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [evalSuiteId, setEvalSuiteId] = useState("");
  const [baseModel, setBaseModel] = useState("gpt-4o-mini-2024-07-18");
  const [systemPrompt, setSystemPrompt] = useState(
    "You are a precise specialist trained on internal documents. Answer clearly: lead with the point, then short supporting detail. Cite the document name when relevant."
  );
  const [jobWebhook, setJobWebhook] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [kb, ev, ds, pipes] = await Promise.all([
        listKnowledge({ pageSize: 50 }).catch(() => ({ data: [] })),
        listEvalSuites().catch(() => []),
        listFineTuneDatasets().catch(() => []),
        listPipelines().catch(() => []),
      ]);
      setKnowledge(kb?.data || []);
      setSuites(ev || []);
      setDatasets(ds || []);
      setPipelines(pipes || []);
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

  const activeJobs = pipelines.filter(
    (p) => !["succeeded", "failed", "cancelled", "completed"].includes(p.status)
  );

  useEffect(() => {
    if (!activeJobs.length) return undefined;
    const id = setInterval(() => {
      listPipelines()
        .then((pipes) => setPipelines(pipes || []))
        .catch(() => {});
    }, 12000);
    return () => clearInterval(id);
  }, [activeJobs.length]);

  async function handleGenerateDataset() {
    if (!selectedKb.length) {
      setError("Select at least one knowledge base");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const row = await createDatasetFromKnowledge({
        knowledge_ids: selectedKb,
        name: datasetName.trim() || "Knowledge training set",
        system_prompt: systemPrompt.trim(),
      });
      setSelectedDataset(String(row.id));
      await load();
    } catch (err) {
      setError(err.message || "Failed to generate dataset");
    } finally {
      setBusy(false);
    }
  }

  async function handleTrain() {
    if (!selectedDataset) {
      setError("Select or generate a dataset first");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await trainAndEval({
        dataset_id: Number(selectedDataset),
        base_model: baseModel,
        auto_eval_suite_id: evalSuiteId ? Number(evalSuiteId) : undefined,
        webhook_url: jobWebhook.trim() || undefined,
      });
      await load();
    } catch (err) {
      setError(err.message || "Training failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRefresh(jobId) {
    setBusy(true);
    try {
      await refreshPipelineJob(jobId);
      await load();
    } catch (err) {
      setError(err.message || "Refresh failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleKb(id) {
    setSelectedKb((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function handleDeploy(job) {
    setBusy(true);
    setError("");
    try {
      const res = await deployPipelineAssistant(job.id, {
        name: `FT · ${job.fine_tuned_model || `Job ${job.id}`}`,
        activate: true,
      });
      const path = res?.chat_path || (res?.assistant?.id ? `/chat?app=${res.assistant.id}` : "/chat");
      router.push(path);
    } catch (err) {
      setError(err.message || "Deploy failed");
    } finally {
      setBusy(false);
    }
  }

  const canDeploy = (job) =>
    ["succeeded", "completed"].includes(job.status) && Boolean(job.fine_tuned_model);

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />
        <main className="workspace-page-main mx-auto max-w-6xl px-4 py-10 sm:px-6">
          <WorkspaceHero
            eyebrow="Model Lab"
            title="Train & auto-test from knowledge"
            description="Turn knowledge bases into fine-tune datasets, launch OpenAI training jobs, and optionally run eval suites when training completes. Add an OpenAI API key under Settings → Model providers first (embeddings + training use the vault key)."
          />

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <WorkspaceStatCard label="Knowledge bases" value={knowledge.length} />
            <WorkspaceStatCard label="Datasets" value={datasets.length} />
            <WorkspaceStatCard label="Active jobs" value={activeJobs.length} />
          </div>

          {error && <WorkspaceAlert type="error" className="mt-6">{error}</WorkspaceAlert>}

          {loading ? (
            <WorkspaceLoading className="mt-10" message="Loading Model Lab…" />
          ) : (
            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ease }}
                className="workspace-panel rounded-[1.5rem] p-5"
              >
                <h2 className="text-lg font-semibold">1. Knowledge → dataset</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  Select knowledge bases to generate training rows automatically.
                </p>
                <div className="mt-4 max-h-48 space-y-2 overflow-y-auto">
                  {knowledge.length === 0 ? (
                    <p className="text-sm text-neutral-500">
                      No knowledge bases.{" "}
                      <Link href="/knowledge" className="font-medium text-neutral-900 underline">
                        Create one
                      </Link>
                    </p>
                  ) : (
                    knowledge.map((kb) => (
                      <label
                        key={kb.id}
                        className="flex cursor-pointer items-center gap-3 rounded-xl border border-black/[0.06] bg-white/80 px-3 py-2.5"
                      >
                        <input
                          type="checkbox"
                          checked={selectedKb.includes(kb.id)}
                          onChange={() => toggleKb(kb.id)}
                        />
                        <span className="text-sm font-medium">{kb.name}</span>
                      </label>
                    ))
                  )}
                </div>
                <input
                  className="input-field mt-4 w-full text-sm"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder="Dataset name"
                />
                <textarea
                  className="input-field mt-3 w-full resize-none text-sm"
                  rows={2}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="System prompt for training rows"
                />
                <button
                  type="button"
                  disabled={busy || !selectedKb.length}
                  onClick={handleGenerateDataset}
                  className="btn-primary mt-4 w-full"
                >
                  Generate dataset
                </button>
              </motion.section>

              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05, ease }}
                className="workspace-panel rounded-[1.5rem] p-5"
              >
                <h2 className="text-lg font-semibold">2. Train & auto-eval</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  Start fine-tuning and optionally attach an eval suite for automatic testing.
                </p>
                <label className="mt-4 block text-xs font-semibold text-neutral-600">
                  Dataset
                  <select
                    className="input-field mt-2 w-full text-sm"
                    value={selectedDataset}
                    onChange={(e) => setSelectedDataset(e.target.value)}
                  >
                    <option value="">Select dataset…</option>
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.row_count} rows)
                      </option>
                    ))}
                  </select>
                </label>
                <label className="mt-4 block text-xs font-semibold text-neutral-600">
                  Base model
                  <input
                    className="input-field mt-2 w-full text-sm"
                    value={baseModel}
                    onChange={(e) => setBaseModel(e.target.value)}
                  />
                </label>
                <label className="mt-4 block text-xs font-semibold text-neutral-600">
                  Auto-eval suite (optional)
                  <select
                    className="input-field mt-2 w-full text-sm"
                    value={evalSuiteId}
                    onChange={(e) => setEvalSuiteId(e.target.value)}
                  >
                    <option value="">None</option>
                    {suites.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="mt-4 block text-xs font-semibold text-neutral-600">
                  Completion webhook (optional)
                  <input
                    className="input-field mt-2 w-full text-sm"
                    value={jobWebhook}
                    onChange={(e) => setJobWebhook(e.target.value)}
                    placeholder="https://hooks.example.com/finetune-done"
                  />
                </label>
                <button
                  type="button"
                  disabled={busy || !selectedDataset}
                  onClick={handleTrain}
                  className="btn-primary mt-4 w-full"
                >
                  Start training pipeline
                </button>
                <p className="mt-3 text-xs text-neutral-500">
                  More eval tools in{" "}
                  <Link href="/evaluation" className="font-medium underline">
                    Evaluation
                  </Link>
                  .
                </p>
              </motion.section>

              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, ease }}
                className="workspace-panel rounded-[1.5rem] p-5 lg:col-span-2"
              >
                <h2 className="text-lg font-semibold">Training pipelines</h2>
                {pipelines.length === 0 ? (
                  <p className="mt-4 text-sm text-neutral-500">No jobs yet.</p>
                ) : (
                  <ul className="mt-4 divide-y divide-black/[0.06]">
                    {pipelines.map((job) => (
                      <li key={job.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold">
                            Job #{job.id} · {job.status}
                          </p>
                          <p className="text-xs text-neutral-500">
                            {job.base_model}
                            {job.fine_tuned_model ? ` → ${job.fine_tuned_model}` : ""}
                            {job.auto_eval_run_id
                              ? ` · auto-eval run #${job.auto_eval_run_id}`
                              : job.auto_eval_suite_id
                                ? " · eval pending"
                                : ""}
                          </p>
                          {job.auto_eval && (
                            <p className="mt-1 text-xs text-emerald-700">
                              Eval: {job.auto_eval.pass_count}/{job.auto_eval.total_count} passed
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleRefresh(job.id)}
                            className="btn-secondary text-xs"
                          >
                            Refresh
                          </button>
                          {canDeploy(job) && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => handleDeploy(job)}
                              className="btn-primary text-xs"
                            >
                              Deploy to Chat
                            </button>
                          )}
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
