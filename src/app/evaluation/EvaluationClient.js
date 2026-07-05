"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { getUserInfo } from "@/lib/api/auth";
import { getAssistantsPage } from "@/lib/api/apps";
import {
  listEvalSuites,
  getEvalSuite,
  createEvalSuite,
  deleteEvalSuite,
  runEvalSuite,
} from "@/lib/api/evaluation";
import {
  listFineTuneDatasets,
  createFineTuneDataset,
  deleteFineTuneDataset,
  listFineTuneJobs,
  startFineTuneJob,
  refreshFineTuneJob,
} from "@/lib/api/finetune";

const ease = [0.16, 1, 0.3, 1];

export default function EvaluationClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState("benchmark");
  const [suites, setSuites] = useState([]);
  const [selectedSuite, setSelectedSuite] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [assistants, setAssistants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [lastRun, setLastRun] = useState(null);

  const [newSuite, setNewSuite] = useState({ name: "", assistant_id: "", caseInput: "", caseExpected: "" });
  const [newDataset, setNewDataset] = useState({
    name: "",
    system: "You are a helpful assistant.",
    user: "",
    assistant: "",
  });

  const readOnly = user?.role === "viewer";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, d, j, apps] = await Promise.all([
        listEvalSuites().catch(() => []),
        listFineTuneDatasets().catch(() => []),
        listFineTuneJobs().catch(() => []),
        getAssistantsPage({ limit: 50 }).catch(() => ({ data: [] })),
      ]);
      setSuites(Array.isArray(s) ? s : []);
      setDatasets(Array.isArray(d) ? d : []);
      setJobs(Array.isArray(j) ? j : []);
      setAssistants(apps?.data || []);
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

  async function openSuite(id) {
    setError("");
    try {
      const detail = await getEvalSuite(id);
      setSelectedSuite(detail);
      setLastRun(null);
    } catch (err) {
      setError(err.message || "Failed to load suite");
    }
  }

  async function handleCreateSuite(e) {
    e.preventDefault();
    if (!newSuite.name.trim() || !newSuite.assistant_id) return;
    setBusy(true);
    setError("");
    try {
      const cases = [];
      if (newSuite.caseInput.trim()) {
        cases.push({
          input: newSuite.caseInput.trim(),
          expected: newSuite.caseExpected.trim(),
          match_type: "contains",
        });
      }
      await createEvalSuite({
        name: newSuite.name.trim(),
        assistant_id: newSuite.assistant_id,
        cases,
      });
      setNewSuite({ name: "", assistant_id: "", caseInput: "", caseExpected: "" });
      await load();
    } catch (err) {
      setError(err.message || "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRunSuite() {
    if (!selectedSuite) return;
    setBusy(true);
    setError("");
    try {
      const run = await runEvalSuite(selectedSuite.id);
      setLastRun(run);
      await openSuite(selectedSuite.id);
    } catch (err) {
      setError(err.message || "Run failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateDataset(e) {
    e.preventDefault();
    if (!newDataset.name.trim() || !newDataset.user.trim() || !newDataset.assistant.trim()) return;
    setBusy(true);
    setError("");
    try {
      await createFineTuneDataset({
        name: newDataset.name.trim(),
        rows: [
          {
            system: newDataset.system.trim(),
            user: newDataset.user.trim(),
            assistant: newDataset.assistant.trim(),
          },
        ],
      });
      setNewDataset({ name: "", system: "You are a helpful assistant.", user: "", assistant: "" });
      await load();
    } catch (err) {
      setError(err.message || "Create dataset failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleStartJob(datasetId) {
    setBusy(true);
    setError("");
    try {
      await startFineTuneJob({ dataset_id: datasetId });
      await load();
    } catch (err) {
      setError(err.message || "Start job failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRefreshJob(jobId) {
    setBusy(true);
    try {
      await refreshFineTuneJob(jobId);
      await load();
    } catch (err) {
      setError(err.message || "Refresh failed");
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="relative flex min-h-screen items-center justify-center">
        <WorkspaceLiveBackground />
        <span className="relative z-10 text-neutral-500">Loading…</span>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />
        <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
          <WorkspaceHero
            eyebrow="Quality"
            title="Evaluation &"
            titleHighlight="fine-tune"
            description="Benchmark assistants with test cases and launch OpenAI fine-tuning jobs from training datasets."
          />

          <div className="mt-8 flex gap-2">
            {["benchmark", "finetune"].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`rounded-full px-4 py-2 text-sm font-semibold capitalize ${
                  tab === t ? "bg-neutral-900 text-white" : "bg-white/70 text-neutral-600 ring-1 ring-black/5"
                }`}
              >
                {t === "benchmark" ? "Benchmarks" : "Fine-tune"}
              </button>
            ))}
          </div>

          {error && (
            <p className="mt-4 rounded-xl border border-red-100 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>
          )}

          {tab === "benchmark" && (
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="workspace-panel rounded-[1.5rem] p-5"
              >
                <h2 className="text-lg font-semibold">Benchmark suites</h2>
                {loading ? (
                  <p className="mt-4 text-sm text-neutral-500">Loading…</p>
                ) : suites.length === 0 ? (
                  <p className="mt-4 text-sm text-neutral-500">No suites yet. Create one below.</p>
                ) : (
                  <ul className="mt-4 space-y-2">
                    {suites.map((s) => (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => openSuite(s.id)}
                          className={`workspace-list-row w-full rounded-xl px-4 py-3 text-left ${
                            selectedSuite?.id === s.id ? "ring-2 ring-neutral-900/20" : ""
                          }`}
                        >
                          <p className="font-medium">{s.name}</p>
                          <p className="text-xs text-neutral-500">{s.case_count} cases</p>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {!readOnly && (
                  <form onSubmit={handleCreateSuite} className="mt-6 space-y-3 border-t border-black/5 pt-5">
                    <h3 className="text-sm font-semibold">New suite</h3>
                    <input
                      className="input-field w-full"
                      placeholder="Suite name"
                      value={newSuite.name}
                      onChange={(e) => setNewSuite((p) => ({ ...p, name: e.target.value }))}
                      required
                    />
                    <select
                      className="input-field w-full"
                      value={newSuite.assistant_id}
                      onChange={(e) => setNewSuite((p) => ({ ...p, assistant_id: e.target.value }))}
                      required
                    >
                      <option value="">Select assistant…</option>
                      {assistants.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                    <textarea
                      className="input-field w-full resize-none"
                      rows={2}
                      placeholder="First test question"
                      value={newSuite.caseInput}
                      onChange={(e) => setNewSuite((p) => ({ ...p, caseInput: e.target.value }))}
                    />
                    <input
                      className="input-field w-full"
                      placeholder="Expected answer (substring match)"
                      value={newSuite.caseExpected}
                      onChange={(e) => setNewSuite((p) => ({ ...p, caseExpected: e.target.value }))}
                    />
                    <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
                      Create suite
                    </button>
                  </form>
                )}
              </motion.section>

              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="workspace-panel rounded-[1.5rem] p-5"
              >
                <h2 className="text-lg font-semibold">Run results</h2>
                {!selectedSuite ? (
                  <p className="mt-4 text-sm text-neutral-500">Select a suite to view cases and run benchmarks.</p>
                ) : (
                  <>
                    <p className="mt-2 text-sm text-neutral-600">
                      {selectedSuite.name} · {selectedSuite.cases?.length || 0} cases
                    </p>
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={handleRunSuite}
                        disabled={busy || !selectedSuite.cases?.length}
                        className="btn-primary mt-4 disabled:opacity-50"
                      >
                        {busy ? "Running…" : "Run benchmark"}
                      </button>
                    )}
                    {lastRun && (
                      <div className="mt-4 rounded-xl bg-emerald-50/80 px-4 py-3 text-sm">
                        <p className="font-semibold text-emerald-800">
                          {lastRun.pass_count}/{lastRun.total_count} passed ({lastRun.pass_rate}%)
                        </p>
                        <p className="text-emerald-700">Avg latency {lastRun.avg_latency_ms}ms</p>
                      </div>
                    )}
                    <ul className="mt-4 max-h-80 space-y-2 overflow-y-auto">
                      {(lastRun?.results || selectedSuite.cases || []).map((item, i) => (
                        <li
                          key={item.case_id || item.id || i}
                          className={`rounded-lg border px-3 py-2 text-xs ${
                            item.passed === false
                              ? "border-red-200 bg-red-50/50"
                              : item.passed
                                ? "border-emerald-200 bg-emerald-50/50"
                                : "border-black/5 bg-white/60"
                          }`}
                        >
                          <p className="font-medium text-neutral-800">{item.input}</p>
                          {item.expected && <p className="text-neutral-500">Expected: {item.expected}</p>}
                          {item.output && <p className="mt-1 text-neutral-700">→ {item.output.slice(0, 200)}</p>}
                        </li>
                      ))}
                    </ul>
                    {!readOnly && selectedSuite && (
                      <button
                        type="button"
                        onClick={async () => {
                          if (!window.confirm("Delete this suite?")) return;
                          await deleteEvalSuite(selectedSuite.id);
                          setSelectedSuite(null);
                          await load();
                        }}
                        className="workspace-btn-ghost workspace-btn-danger mt-4 text-sm"
                      >
                        Delete suite
                      </button>
                    )}
                  </>
                )}
              </motion.section>
            </div>
          )}

          {tab === "finetune" && (
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <motion.section className="workspace-panel rounded-[1.5rem] p-5">
                <h2 className="text-lg font-semibold">Training datasets</h2>
                <ul className="mt-4 space-y-2">
                  {datasets.map((d) => (
                    <li key={d.id} className="workspace-list-row rounded-xl px-4 py-3">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className="font-medium">{d.name}</p>
                          <p className="text-xs text-neutral-500">{d.row_count} rows</p>
                        </div>
                        {!readOnly && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleStartJob(d.id)}
                            className="workspace-btn-ghost !py-1.5 text-xs"
                          >
                            Start job
                          </button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
                {!readOnly && (
                  <form onSubmit={handleCreateDataset} className="mt-6 space-y-3 border-t border-black/5 pt-5">
                    <h3 className="text-sm font-semibold">New dataset</h3>
                    <input
                      className="input-field w-full"
                      placeholder="Dataset name"
                      value={newDataset.name}
                      onChange={(e) => setNewDataset((p) => ({ ...p, name: e.target.value }))}
                      required
                    />
                    <input
                      className="input-field w-full text-xs"
                      placeholder="System prompt"
                      value={newDataset.system}
                      onChange={(e) => setNewDataset((p) => ({ ...p, system: e.target.value }))}
                    />
                    <textarea
                      className="input-field w-full resize-none"
                      rows={2}
                      placeholder="User message"
                      value={newDataset.user}
                      onChange={(e) => setNewDataset((p) => ({ ...p, user: e.target.value }))}
                      required
                    />
                    <textarea
                      className="input-field w-full resize-none"
                      rows={2}
                      placeholder="Ideal assistant reply"
                      value={newDataset.assistant}
                      onChange={(e) => setNewDataset((p) => ({ ...p, assistant: e.target.value }))}
                      required
                    />
                    <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
                      Create dataset
                    </button>
                  </form>
                )}
              </motion.section>

              <motion.section className="workspace-panel rounded-[1.5rem] p-5">
                <h2 className="text-lg font-semibold">Fine-tune jobs</h2>
                <p className="mt-1 text-xs text-neutral-500">OpenAI-compatible providers only. Uses active provider key if unset.</p>
                <ul className="mt-4 space-y-2">
                  {jobs.map((j) => (
                    <li key={j.id} className="workspace-list-row rounded-xl px-4 py-3 text-sm">
                      <p className="font-medium">
                        Job #{j.id}{" "}
                        <span className="text-xs font-normal text-neutral-500">({j.status})</span>
                      </p>
                      {j.fine_tuned_model && (
                        <p className="mt-1 font-mono text-xs text-emerald-700">{j.fine_tuned_model}</p>
                      )}
                      {j.error_message && <p className="mt-1 text-xs text-red-600">{j.error_message}</p>}
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleRefreshJob(j.id)}
                        className="workspace-btn-ghost mt-2 !py-1 text-xs"
                      >
                        Refresh status
                      </button>
                    </li>
                  ))}
                </ul>
              </motion.section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
