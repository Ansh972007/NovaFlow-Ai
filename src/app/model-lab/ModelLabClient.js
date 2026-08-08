"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import AnimatedCounter from "@/components/AnimatedCounter";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { listKnowledge } from "@/lib/api/knowledge";
import { listEvalSuites } from "@/lib/api/evaluation";
import { listFineTuneDatasets, getFineTuneDataset } from "@/lib/api/finetune";
import { humanizeFinetuneError } from "@/lib/humanizeErrors";
import {
  createDatasetFromKnowledge,
  trainAndEval,
  listPipelines,
  refreshPipelineJob,
  deployPipelineAssistant,
} from "@/lib/api/modelLab";

const ease = [0.16, 1, 0.3, 1];

const BASE_MODEL_PRESETS = [
  "gpt-4o-mini-2024-07-18",
  "gpt-4o-2024-08-06",
  "gpt-3.5-turbo",
];

const DONE_STATUSES = new Set(["succeeded", "failed", "cancelled", "completed"]);
const OK_STATUSES = new Set(["succeeded", "completed"]);

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function PipelineStatusBadge({ status }) {
  const failed = status === "failed" || status === "cancelled";
  const done = OK_STATUSES.has(status);
  const active = !DONE_STATUSES.has(status);

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-wide uppercase ${
        failed
          ? "border-black bg-white text-black"
          : done
            ? "border-black bg-black text-white"
            : "border-dashed border-black bg-neutral-50 text-black"
      }`}
    >
      {active && (
        <motion.span
          className="h-1.5 w-1.5 rounded-full bg-black"
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.2, repeat: Infinity }}
        />
      )}
      {status || "unknown"}
    </span>
  );
}

function StepHeader({ step, title, description }) {
  return (
    <div>
      <p className="workspace-section-label">Step {step}</p>
      <h2 className="mt-1 font-serif text-xl tracking-tight text-neutral-900 sm:text-2xl">{title}</h2>
      {description && <p className="mt-2 text-sm leading-relaxed text-neutral-500">{description}</p>}
    </div>
  );
}

function KbSelectCard({ kb, selected, onToggle }) {
  return (
    <motion.button
      type="button"
      onClick={onToggle}
      whileHover={{ x: 2 }}
      whileTap={{ scale: 0.99 }}
      className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition ${
        selected
          ? "border-black bg-neutral-50 shadow-sm"
          : "border-neutral-200 bg-white hover:border-neutral-400"
      }`}
    >
      <span
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition ${
          selected ? "border-black bg-black text-white" : "border-neutral-300 bg-white"
        }`}
      >
        {selected && (
          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <path d="M5 12.5 9.5 17 19 7" />
          </svg>
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-neutral-900">{kb.name}</span>
        {kb.description && <span className="block truncate text-[11px] text-neutral-400">{kb.description}</span>}
      </span>
    </motion.button>
  );
}

function PipelineJobCard({ job, busy, onRefresh, onDeploy, onCopyModel, canDeploy, index }) {
  const evalPct =
    job.auto_eval?.total_count > 0
      ? Math.round((job.auto_eval.pass_count / job.auto_eval.total_count) * 100)
      : null;

  return (
    <motion.li
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35, ease }}
      whileHover={{ x: 3 }}
      className="workspace-panel noise rounded-2xl p-4 sm:p-5"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-neutral-900">Job #{job.id}</p>
            <PipelineStatusBadge status={job.status} />
          </div>
          <p className="mt-2 font-mono text-xs text-neutral-600">{job.base_model}</p>
          {job.fine_tuned_model && (
            <p className="mt-1 truncate font-mono text-xs text-neutral-500">→ {job.fine_tuned_model}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {job.auto_eval_run_id && (
              <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                Eval run #{job.auto_eval_run_id}
              </span>
            )}
            {job.auto_eval_suite_id && !job.auto_eval_run_id && (
              <span className="rounded-full border border-dashed border-neutral-300 px-2 py-0.5 text-[10px] font-medium text-neutral-500">
                Eval pending
              </span>
            )}
            <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-500">
              {fmtTime(job.create_time)}
            </span>
          </div>
          {job.auto_eval && (
            <div className="mt-3 rounded-xl border border-black/[0.06] bg-neutral-50 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] font-semibold text-neutral-800">Auto-eval score</p>
                <p className="text-[11px] font-bold text-neutral-900">
                  {job.auto_eval.pass_count}/{job.auto_eval.total_count}
                  {evalPct != null ? ` · ${evalPct}%` : ""}
                </p>
              </div>
              {evalPct != null && (
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-200">
                  <motion.div
                    className="h-full rounded-full bg-black"
                    initial={{ width: 0 }}
                    animate={{ width: `${evalPct}%` }}
                    transition={{ duration: 0.8, ease }}
                  />
                </div>
              )}
            </div>
          )}
          {job.error_message && (
            <p className="mt-2 text-xs leading-relaxed text-red-700">{humanizeFinetuneError(job.error_message)}</p>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button type="button" disabled={busy} onClick={() => onRefresh(job.id)} className="btn-secondary text-xs disabled:opacity-50">
            Refresh
          </button>
          {canDeploy(job) && job.fine_tuned_model && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onCopyModel(job)}
              className="btn-secondary text-xs disabled:opacity-50"
            >
              Copy model ID
            </button>
          )}
          {canDeploy(job) && (
            <button type="button" disabled={busy} onClick={() => onDeploy(job)} className="btn-primary text-xs disabled:opacity-50">
              Test in Chat
            </button>
          )}
        </div>
      </div>
    </motion.li>
  );
}

export default function ModelLabClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
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
      setError("");
    } catch (err) {
      setError(err.message || "Failed to load Model Lab");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then((u) => {
        if (!u) {
          router.replace("/login");
          return;
        }
        setUser(u);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const activeJobs = useMemo(
    () => pipelines.filter((p) => !DONE_STATUSES.has(p.status)),
    [pipelines]
  );

  const completedJobs = useMemo(
    () => pipelines.filter((p) => OK_STATUSES.has(p.status)).length,
    [pipelines]
  );

  const totalRows = useMemo(
    () => datasets.reduce((s, d) => s + (d.row_count || 0), 0),
    [datasets]
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
    setMsg("");
    try {
      const row = await createDatasetFromKnowledge({
        knowledge_ids: selectedKb,
        name: datasetName.trim() || "Knowledge training set",
        system_prompt: systemPrompt.trim(),
      });
      setSelectedDataset(String(row.id));
      setMsg(`Dataset "${row.name || datasetName}" created with training rows.`);
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
    setMsg("");
    try {
      await trainAndEval({
        dataset_id: Number(selectedDataset),
        base_model: baseModel,
        auto_eval_suite_id: evalSuiteId ? Number(evalSuiteId) : undefined,
        webhook_url: jobWebhook.trim() || undefined,
      });
      setMsg("Training pipeline started. Jobs refresh automatically while active.");
      await load();
    } catch (err) {
      setError(humanizeFinetuneError(err.message || "Training failed"));
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

  async function handleCopyModel(job) {
    const modelId = job.fine_tuned_model;
    if (!modelId) return;
    try {
      await navigator.clipboard.writeText(modelId);
      setMsg(`Model ID copied: ${modelId}`);
      setError("");
    } catch {
      setError("Could not copy model ID to clipboard.");
    }
  }

  async function handleExportDataset() {
    if (!selectedDataset) {
      setError("Select a dataset to export");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const ds = await getFineTuneDataset(Number(selectedDataset));
      const rows = ds?.rows || [];
      const lines = rows
        .map((row) => {
          const system = (row.system || "").trim();
          const user = (row.user || row.prompt || "").trim();
          const assistant = (row.assistant || row.completion || "").trim();
          if (!user || !assistant) return null;
          const messages = [];
          if (system) messages.push({ role: "system", content: system });
          messages.push({ role: "user", content: user });
          messages.push({ role: "assistant", content: assistant });
          return JSON.stringify({ messages });
        })
        .filter(Boolean);
      if (!lines.length) {
        setError("Dataset has no exportable rows.");
        return;
      }
      const blob = new Blob([`${lines.join("\n")}\n`], { type: "application/jsonl" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(ds.name || "dataset").replace(/\s+/g, "_")}.jsonl`;
      a.click();
      URL.revokeObjectURL(url);
      setMsg(`Exported ${lines.length} training rows as JSONL.`);
    } catch (err) {
      setError(err.message || "Export failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeploy(job) {
    setBusy(true);
    setError("");
    setMsg("");
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

  const canDeploy = (job) => OK_STATUSES.has(job.status) && Boolean(job.fine_tuned_model);

  const workflowStep = !selectedDataset ? 1 : activeJobs.length ? 3 : 2;

  return (
    <WorkspacePageShell user={user} loading={loading || !user} loadingMessage="Loading Model Lab…" maxWidth="max-w-7xl">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
        <WorkspaceHero
          eyebrow="Fine-tuning studio"
          title="Model"
          titleHighlight="Lab"
          description="Turn knowledge bases into training datasets and fine-tune with a native OpenAI API key (not OpenRouter). Add your key under Credentials → AI / Models, then train, test in Chat, or export the model ID."
          badge={
            <span className="workspace-badge-live inline-flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-neutral-400 opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-neutral-900" />
              </span>
              {activeJobs.length} active {activeJobs.length === 1 ? "job" : "jobs"}
            </span>
          }
        />

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5, ease }}
          className="mt-8 grid gap-4 sm:grid-cols-3"
        >
          <WorkspaceStatCard
            label="Knowledge bases"
            value={<AnimatedCounter value={String(knowledge.length)} />}
            hint="Available to train on"
          />
          <WorkspaceStatCard
            label="Training rows"
            value={<AnimatedCounter value={String(totalRows)} />}
            hint={`${datasets.length} datasets`}
          />
          <WorkspaceStatCard
            label="Completed jobs"
            value={<AnimatedCounter value={String(completedJobs)} />}
            hint={`${pipelines.length} total pipelines`}
          />
        </motion.div>

        <AnimatePresence mode="wait">
          {(error || msg) && (
            <motion.div
              key={error ? "e" : "m"}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-6 overflow-hidden"
            >
              <WorkspaceAlert type={error ? "error" : "success"}>{error || msg}</WorkspaceAlert>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12, ease }}
          className="mt-8 flex flex-wrap gap-2"
        >
          {[
            { n: 1, label: "Dataset" },
            { n: 2, label: "Train" },
            { n: 3, label: "Deploy" },
          ].map(({ n, label }) => (
            <span
              key={label}
              className={`rounded-full px-4 py-2 text-xs font-semibold transition ${
                workflowStep === n ? "bg-black text-white shadow-md" : workflowStep > n ? "bg-neutral-200 text-neutral-700" : "bg-neutral-100 text-neutral-500"
              }`}
            >
              {n}. {label}
            </span>
          ))}
        </motion.div>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, ease }}
            className="workspace-panel noise rounded-[1.5rem] p-5 sm:p-6"
          >
            <StepHeader
              step={1}
              title="Knowledge → dataset"
              description="Select knowledge bases to auto-generate Q→A training rows with your system prompt."
            />
            <div className="mt-5 max-h-52 space-y-2 overflow-y-auto pr-1">
              {knowledge.length === 0 ? (
                <div className="workspace-empty rounded-xl py-10 text-center">
                  <p className="text-sm text-neutral-500">No knowledge bases yet.</p>
                  <Link href="/knowledge" className="btn-primary mt-4 inline-flex text-sm">
                    Create knowledge base
                  </Link>
                </div>
              ) : (
                knowledge.map((kb) => (
                  <KbSelectCard
                    key={kb.id}
                    kb={kb}
                    selected={selectedKb.includes(kb.id)}
                    onToggle={() => toggleKb(kb.id)}
                  />
                ))
              )}
            </div>
            <label className="mt-5 block">
              <span className="text-xs font-semibold text-neutral-700">Dataset name</span>
              <input
                className="input-field mt-2 w-full text-sm"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="Knowledge training set"
              />
            </label>
            <label className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-700">System prompt for rows</span>
              <textarea
                className="input-field mt-2 w-full resize-y text-sm leading-relaxed"
                rows={3}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
              />
            </label>
            <motion.button
              type="button"
              disabled={busy || !selectedKb.length}
              whileHover={busy ? {} : { scale: 1.01 }}
              whileTap={busy ? {} : { scale: 0.99 }}
              onClick={handleGenerateDataset}
              className="btn-primary mt-5 w-full disabled:opacity-50"
            >
              {busy ? "Generating…" : `Generate dataset · ${selectedKb.length} KB${selectedKb.length === 1 ? "" : "s"}`}
            </motion.button>
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, ease }}
            className="workspace-panel noise rounded-[1.5rem] p-5 sm:p-6"
          >
            <StepHeader
              step={2}
              title="Train & auto-eval"
              description="Start fine-tuning and optionally attach an eval suite for automatic testing on completion."
            />
            <label className="mt-5 block">
              <span className="text-xs font-semibold text-neutral-700">Dataset</span>
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
            <label className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-700">Base model</span>
              <input
                className="input-field mt-2 w-full font-mono text-sm"
                value={baseModel}
                onChange={(e) => setBaseModel(e.target.value)}
                list="base-model-presets"
              />
              <datalist id="base-model-presets">
                {BASE_MODEL_PRESETS.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </label>
            <label className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-700">Auto-eval suite (optional)</span>
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
            <label className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-700">Notify on completion (optional)</span>
              <input
                className="input-field mt-2 w-full text-sm"
                value={jobWebhook}
                onChange={(e) => setJobWebhook(e.target.value)}
                placeholder="Your webhook URL when training finishes"
              />
            </label>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy || !selectedDataset}
                onClick={handleExportDataset}
                className="btn-secondary text-sm disabled:opacity-50"
              >
                Export JSONL
              </button>
            </div>
            <motion.button
              type="button"
              disabled={busy || !selectedDataset}
              whileHover={busy ? {} : { scale: 1.01 }}
              whileTap={busy ? {} : { scale: 0.99 }}
              onClick={handleTrain}
              className="btn-primary mt-5 w-full disabled:opacity-50"
            >
              {busy ? "Starting…" : "Start training pipeline"}
            </motion.button>
            <p className="mt-4 text-xs text-neutral-500">
              Requires a native{" "}
              <Link href="/credentials" className="font-medium text-neutral-800 underline">
                OpenAI API key
              </Link>
              . More eval tools in{" "}
              <Link href="/evaluation" className="font-medium text-neutral-800 underline">
                Evaluation
              </Link>
            </p>
          </motion.section>
        </div>

        <section className="mt-10">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="workspace-section-label">Step 3</p>
              <h2 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900">Training pipelines</h2>
              <p className="mt-1 text-sm text-neutral-500">Active jobs poll every 12s. Test completed models in Chat or copy the model ID for export.</p>
            </div>
            <button type="button" onClick={load} disabled={busy} className="workspace-btn-ghost text-sm disabled:opacity-50">
              Refresh all
            </button>
          </div>

          {pipelines.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="workspace-empty rounded-[1.5rem] py-16 text-center"
            >
              <p className="font-semibold text-neutral-900">No training jobs yet</p>
              <p className="mt-2 text-sm text-neutral-500">Generate a dataset and start a pipeline to see jobs here.</p>
            </motion.div>
          ) : (
            <ul className="space-y-3">
              {pipelines.map((job, i) => (
                <PipelineJobCard
                  key={job.id}
                  job={job}
                  index={i}
                  busy={busy}
                  onRefresh={handleRefresh}
                  onDeploy={handleDeploy}
                  onCopyModel={handleCopyModel}
                  canDeploy={canDeploy}
                />
              ))}
            </ul>
          )}
        </section>
      </motion.div>
    </WorkspacePageShell>
  );
}
