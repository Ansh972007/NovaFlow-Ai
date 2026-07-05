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
  importEvalCasesCsv,
  compareEvalSuite,
  listEvalSchedules,
  createEvalSchedule,
  deleteEvalSchedule,
  triggerEvalSchedule,
  updateEvalSchedule,
} from "@/lib/api/evaluation";
import {
  listFineTuneDatasets,
  createFineTuneDataset,
  deleteFineTuneDataset,
  listFineTuneJobs,
  startFineTuneJob,
  refreshFineTuneJob,
  importFineTuneCsv,
  applyFineTuneJob,
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
  const [scoringMode, setScoringMode] = useState("rules");
  const [csvBusy, setCsvBusy] = useState(false);
  const [schedules, setSchedules] = useState([]);
  const [compareSuiteId, setCompareSuiteId] = useState("");
  const [compareIds, setCompareIds] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [jobWebhook, setJobWebhook] = useState("");
  const [newSchedule, setNewSchedule] = useState({
    suite_id: "",
    interval_hours: 24,
    webhook_url: "",
    scoring: "rules",
  });

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
      const [s, d, j, apps, sched] = await Promise.all([
        listEvalSuites().catch(() => []),
        listFineTuneDatasets().catch(() => []),
        listFineTuneJobs().catch(() => []),
        getAssistantsPage({ limit: 50 }).catch(() => ({ data: [] })),
        listEvalSchedules().catch(() => []),
      ]);
      setSuites(Array.isArray(s) ? s : []);
      setDatasets(Array.isArray(d) ? d : []);
      setJobs(Array.isArray(j) ? j : []);
      setAssistants(apps?.data || []);
      setSchedules(Array.isArray(sched) ? sched : []);
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
      const run = await runEvalSuite(selectedSuite.id, {
        scoring: scoringMode,
        judge_threshold: 4,
      });
      setLastRun(run);
      await openSuite(selectedSuite.id);
    } catch (err) {
      setError(err.message || "Run failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleImportCasesCsv(e) {
    const file = e.target.files?.[0];
    if (!file || !selectedSuite) return;
    setCsvBusy(true);
    setError("");
    try {
      const text = await file.text();
      await importEvalCasesCsv(selectedSuite.id, text);
      await openSuite(selectedSuite.id);
      await load();
    } catch (err) {
      setError(err.message || "CSV import failed");
    } finally {
      setCsvBusy(false);
      e.target.value = "";
    }
  }

  async function handleImportDatasetCsv(datasetId, e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvBusy(true);
    setError("");
    try {
      const text = await file.text();
      await importFineTuneCsv(datasetId, text);
      await load();
    } catch (err) {
      setError(err.message || "CSV import failed");
    } finally {
      setCsvBusy(false);
      e.target.value = "";
    }
  }

  async function handleApplyJob(jobId) {
    setBusy(true);
    setError("");
    try {
      await applyFineTuneJob(jobId, { activate: true });
      await load();
    } catch (err) {
      setError(err.message || "Apply model failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleCompareId(id) {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 5 ? [...prev, id] : prev
    );
  }

  async function handleCompare() {
    if (!compareSuiteId || compareIds.length < 2) {
      setError("Select a suite and at least two assistants");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await compareEvalSuite(Number(compareSuiteId), {
        assistant_ids: compareIds,
        scoring: scoringMode,
        judge_threshold: 4,
      });
      setComparison(result);
    } catch (err) {
      setError(err.message || "Comparison failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateSchedule(e) {
    e.preventDefault();
    if (!newSchedule.suite_id) return;
    setBusy(true);
    setError("");
    try {
      await createEvalSchedule({
        suite_id: Number(newSchedule.suite_id),
        interval_hours: Number(newSchedule.interval_hours) || 24,
        webhook_url: newSchedule.webhook_url.trim(),
        scoring: newSchedule.scoring,
        enabled: true,
      });
      setNewSchedule({ suite_id: "", interval_hours: 24, webhook_url: "", scoring: "rules" });
      await load();
    } catch (err) {
      setError(err.message || "Create schedule failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleSchedule(sched) {
    setBusy(true);
    try {
      await updateEvalSchedule(sched.id, { enabled: !sched.enabled });
      await load();
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleTriggerSchedule(id) {
    setBusy(true);
    setError("");
    try {
      await triggerEvalSchedule(id);
      await load();
    } catch (err) {
      setError(err.message || "Trigger failed");
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
      await startFineTuneJob({
        dataset_id: datasetId,
        webhook_url: jobWebhook.trim(),
      });
      setJobWebhook("");
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

          <div className="mt-8 flex flex-wrap gap-2">
            {[
              { id: "benchmark", label: "Benchmarks" },
              { id: "compare", label: "Compare" },
              { id: "schedules", label: "Schedules" },
              { id: "finetune", label: "Fine-tune" },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  tab === t.id ? "bg-neutral-900 text-white" : "bg-white/70 text-neutral-600 ring-1 ring-black/5"
                }`}
              >
                {t.label}
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
                      <div className="mt-4 flex flex-wrap items-center gap-3">
                        <label className="flex items-center gap-2 text-sm text-neutral-600">
                          Scoring
                          <select
                            className="input-field !py-1.5 text-sm"
                            value={scoringMode}
                            onChange={(e) => setScoringMode(e.target.value)}
                          >
                            <option value="rules">Rules (contains / exact)</option>
                            <option value="judge">LLM judge</option>
                          </select>
                        </label>
                        <button
                          type="button"
                          onClick={handleRunSuite}
                          disabled={busy || !selectedSuite.cases?.length}
                          className="btn-primary disabled:opacity-50"
                        >
                          {busy ? "Running…" : "Run benchmark"}
                        </button>
                        <label className="workspace-btn-ghost cursor-pointer !py-1.5 text-xs">
                          {csvBusy ? "Importing…" : "Import CSV"}
                          <input
                            type="file"
                            accept=".csv,text/csv"
                            className="hidden"
                            disabled={csvBusy}
                            onChange={handleImportCasesCsv}
                          />
                        </label>
                      </div>
                    )}
                    <p className="mt-2 text-xs text-neutral-400">
                      CSV columns: input, expected, match_type (optional)
                    </p>
                    {lastRun && (
                      <div className="mt-4 rounded-xl bg-emerald-50/80 px-4 py-3 text-sm">
                        <p className="font-semibold text-emerald-800">
                          {lastRun.pass_count}/{lastRun.total_count} passed ({lastRun.pass_rate}%)
                        </p>
                        <p className="text-emerald-700">
                          Avg latency {lastRun.avg_latency_ms}ms
                          {lastRun.scoring === "judge" && " · LLM judge"}
                        </p>
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
                          {item.judge_score != null && (
                            <p className="mt-1 text-neutral-500">
                              Judge: {item.judge_score}/5 — {item.judge_reason}
                            </p>
                          )}
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

          {tab === "compare" && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="workspace-panel mt-6 rounded-[1.5rem] p-5"
            >
              <h2 className="text-lg font-semibold">Multi-assistant comparison</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Run the same benchmark suite against multiple assistants side-by-side.
              </p>
              {!readOnly && (
                <div className="mt-4 space-y-3">
                  <select
                    className="input-field w-full"
                    value={compareSuiteId}
                    onChange={(e) => setCompareSuiteId(e.target.value)}
                  >
                    <option value="">Select benchmark suite…</option>
                    {suites.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.case_count} cases)
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-neutral-500">Select 2–5 assistants:</p>
                  <div className="flex flex-wrap gap-2">
                    {assistants.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        onClick={() => toggleCompareId(a.id)}
                        className={`rounded-full px-3 py-1.5 text-xs font-medium ${
                          compareIds.includes(a.id)
                            ? "bg-neutral-900 text-white"
                            : "bg-white/70 text-neutral-600 ring-1 ring-black/5"
                        }`}
                      >
                        {a.name}
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    disabled={busy || compareIds.length < 2 || !compareSuiteId}
                    onClick={handleCompare}
                    className="btn-primary disabled:opacity-50"
                  >
                    {busy ? "Comparing…" : "Run comparison"}
                  </button>
                </div>
              )}
              {comparison?.assistants?.length > 0 && (
                <div className="mt-6 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-black/5 text-left text-xs text-neutral-500">
                        <th className="py-2 pr-4">Assistant</th>
                        <th className="py-2 pr-4">Pass rate</th>
                        <th className="py-2 pr-4">Passed</th>
                        <th className="py-2">Avg latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...comparison.assistants]
                        .sort((a, b) => b.pass_rate - a.pass_rate)
                        .map((a) => (
                          <tr key={a.assistant_id} className="border-b border-black/5">
                            <td className="py-2 pr-4 font-medium">{a.assistant_name}</td>
                            <td className="py-2 pr-4 text-emerald-700">{a.pass_rate}%</td>
                            <td className="py-2 pr-4">
                              {a.pass_count}/{a.total_count}
                            </td>
                            <td className="py-2">{a.avg_latency_ms}ms</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </motion.section>
          )}

          {tab === "schedules" && (
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <motion.section className="workspace-panel rounded-[1.5rem] p-5">
                <h2 className="text-lg font-semibold">Scheduled runs</h2>
                <p className="mt-1 text-xs text-neutral-500">
                  Auto-run benchmarks on an interval. Optional webhook fires on each completion.
                </p>
                <ul className="mt-4 space-y-2">
                  {schedules.map((sched) => {
                    const suite = suites.find((s) => s.id === sched.suite_id);
                    return (
                      <li key={sched.id} className="workspace-list-row rounded-xl px-4 py-3 text-sm">
                        <p className="font-medium">
                          {suite?.name || `Suite #${sched.suite_id}`}
                          <span className="ml-2 text-xs font-normal text-neutral-500">
                            every {sched.interval_hours}h · {sched.enabled ? "on" : "off"}
                          </span>
                        </p>
                        {sched.next_run_at && (
                          <p className="text-xs text-neutral-500">Next: {new Date(sched.next_run_at).toLocaleString()}</p>
                        )}
                        {!readOnly && (
                          <div className="mt-2 flex flex-wrap gap-2">
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => handleToggleSchedule(sched)}
                              className="workspace-btn-ghost !py-1 text-xs"
                            >
                              {sched.enabled ? "Pause" : "Resume"}
                            </button>
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => handleTriggerSchedule(sched.id)}
                              className="workspace-btn-ghost !py-1 text-xs"
                            >
                              Run now
                            </button>
                            <button
                              type="button"
                              disabled={busy}
                              onClick={async () => {
                                await deleteEvalSchedule(sched.id);
                                await load();
                              }}
                              className="workspace-btn-ghost workspace-btn-danger !py-1 text-xs"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </motion.section>

              {!readOnly && (
                <motion.section className="workspace-panel rounded-[1.5rem] p-5">
                  <h2 className="text-lg font-semibold">New schedule</h2>
                  <form onSubmit={handleCreateSchedule} className="mt-4 space-y-3">
                    <select
                      className="input-field w-full"
                      value={newSchedule.suite_id}
                      onChange={(e) => setNewSchedule((p) => ({ ...p, suite_id: e.target.value }))}
                      required
                    >
                      <option value="">Suite…</option>
                      {suites.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      min={1}
                      className="input-field w-full"
                      placeholder="Interval (hours)"
                      value={newSchedule.interval_hours}
                      onChange={(e) => setNewSchedule((p) => ({ ...p, interval_hours: e.target.value }))}
                    />
                    <select
                      className="input-field w-full"
                      value={newSchedule.scoring}
                      onChange={(e) => setNewSchedule((p) => ({ ...p, scoring: e.target.value }))}
                    >
                      <option value="rules">Rules scoring</option>
                      <option value="judge">LLM judge</option>
                    </select>
                    <input
                      className="input-field w-full text-xs"
                      placeholder="Webhook URL (optional)"
                      value={newSchedule.webhook_url}
                      onChange={(e) => setNewSchedule((p) => ({ ...p, webhook_url: e.target.value }))}
                    />
                    <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
                      Create schedule
                    </button>
                  </form>
                </motion.section>
              )}
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
                          <div className="flex items-center gap-2">
                            <label className="workspace-btn-ghost cursor-pointer !py-1.5 text-xs">
                              CSV
                              <input
                                type="file"
                                accept=".csv,text/csv"
                                className="hidden"
                                disabled={csvBusy}
                                onChange={(e) => handleImportDatasetCsv(d.id, e)}
                              />
                            </label>
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => handleStartJob(d.id)}
                              className="workspace-btn-ghost !py-1.5 text-xs"
                            >
                              Start job
                            </button>
                          </div>
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
                <p className="mt-1 text-xs text-neutral-500">
                  OpenAI-compatible providers only. CSV columns: user, assistant (optional: system)
                </p>
                {!readOnly && (
                  <input
                    className="input-field mt-3 w-full text-xs"
                    placeholder="Webhook URL for job completion (optional)"
                    value={jobWebhook}
                    onChange={(e) => setJobWebhook(e.target.value)}
                  />
                )}
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
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleRefreshJob(j.id)}
                          className="workspace-btn-ghost !py-1 text-xs"
                        >
                          Refresh status
                        </button>
                        {!readOnly && j.fine_tuned_model && j.status === "succeeded" && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleApplyJob(j.id)}
                            className="workspace-btn-ghost !py-1 text-xs text-emerald-700"
                          >
                            Apply to provider
                          </button>
                        )}
                      </div>
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
