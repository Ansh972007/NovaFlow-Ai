"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import WorkspaceEmpty from "@/components/workspace/WorkspaceEmpty";
import WorkspaceTabs, { WorkspaceStatCard, WorkspaceSkeletonList } from "@/components/workspace/WorkspaceTabs";
import { SuiteTrendChart, ComparisonTrendChart } from "@/components/evaluation/EvalTrendCharts";
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
  getSuiteTrends,
  getComparisonTrends,
  listEvalAlerts,
  createEvalAlert,
  deleteEvalAlert,
  updateEvalAlert,
  getEvalRunDiff,
  listEvalTemplates,
  createSuiteFromTemplate,
} from "@/lib/api/evaluation";
import { getPromptDrift } from "@/lib/api/modelLab";
import {
  listFineTuneDatasets,
  createFineTuneDataset,
  deleteFineTuneDataset,
  listFineTuneJobs,
  startFineTuneJob,
  refreshFineTuneJob,
  importFineTuneCsv,
  applyFineTuneJob,
  estimateFineTuneCost,
  listAbRoutes,
  createAbRoute,
  deleteAbRoute,
} from "@/lib/api/finetune";
import { getActiveWorkspaceId, getWorkspaceQuotas, updateWorkspaceQuotas } from "@/lib/api/workspaces";

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
    cron_expression: "",
    webhook_url: "",
    scoring: "rules",
  });
  const [alerts, setAlerts] = useState([]);
  const [trendSuiteId, setTrendSuiteId] = useState("");
  const [suiteTrends, setSuiteTrends] = useState([]);
  const [comparisonTrends, setComparisonTrends] = useState([]);
  const [newAlert, setNewAlert] = useState({
    suite_id: "",
    min_pass_rate: 80,
    drop_points: 10,
    webhook_url: "",
    pagerduty_routing_key: "",
    opsgenie_api_key: "",
    email_to: "",
    use_workspace_slack: true,
  });
  const [runDiff, setRunDiff] = useState(null);
  const [costEstimate, setCostEstimate] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [templatePick, setTemplatePick] = useState({ template_id: "", assistant_id: "" });
  const [abRoutes, setAbRoutes] = useState([]);
  const [newAbRoute, setNewAbRoute] = useState({ base_model: "", variant_model: "", variant_traffic_pct: 50 });
  const [quotas, setQuotas] = useState(null);
  const [driftRadar, setDriftRadar] = useState(null);

  const [newSuite, setNewSuite] = useState({ name: "", assistant_id: "", caseInput: "", caseExpected: "" });
  const [newDataset, setNewDataset] = useState({
    name: "",
    system:
      "You are a precise assistant. Lead with the answer, then short supporting bullets. If information is missing, say so.",
    user: "",
    assistant: "",
  });

  const readOnly = user?.role === "viewer";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, d, j, apps, sched, al, tpl, ab, q] = await Promise.all([
        listEvalSuites().catch(() => []),
        listFineTuneDatasets().catch(() => []),
        listFineTuneJobs().catch(() => []),
        getAssistantsPage({ limit: 50 }).catch(() => ({ data: [] })),
        listEvalSchedules().catch(() => []),
        listEvalAlerts().catch(() => []),
        listEvalTemplates().catch(() => []),
        listAbRoutes().catch(() => []),
        getActiveWorkspaceId()
          ? getWorkspaceQuotas(getActiveWorkspaceId()).catch(() => null)
          : Promise.resolve(null),
      ]);
      setSuites(Array.isArray(s) ? s : []);
      setDatasets(Array.isArray(d) ? d : []);
      setJobs(Array.isArray(j) ? j : []);
      setAssistants(apps?.data || []);
      setSchedules(Array.isArray(sched) ? sched : []);
      setAlerts(Array.isArray(al) ? al : []);
      setTemplates(Array.isArray(tpl) ? tpl : []);
      setAbRoutes(Array.isArray(ab) ? ab : []);
      setQuotas(q);
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
    if (tab !== "trends") return;
    async function loadTrends() {
      const sid = trendSuiteId || suites[0]?.id;
      if (!sid) {
        setSuiteTrends([]);
        setComparisonTrends([]);
        return;
      }
      try {
        const [st, ct] = await Promise.all([
          getSuiteTrends(sid).catch(() => ({ points: [] })),
          getComparisonTrends(sid).catch(() => ({ series: [] })),
        ]);
        setSuiteTrends(st?.points || []);
        setComparisonTrends(ct?.series || []);
        if (!trendSuiteId && sid) setTrendSuiteId(String(sid));
      } catch {
        setSuiteTrends([]);
        setComparisonTrends([]);
      }
    }
    loadTrends();
  }, [tab, trendSuiteId, suites]);

  useEffect(() => {
    if (tab !== "drift") return;
    async function loadDrift() {
      try {
        const data = await getPromptDrift(
          trendSuiteId ? { suite_id: Number(trendSuiteId) } : {}
        );
        setDriftRadar(data);
      } catch {
        setDriftRadar(null);
      }
    }
    loadDrift();
  }, [tab, trendSuiteId]);

  async function openSuite(id) {
    setError("");
    try {
      const detail = await getEvalSuite(id);
      setSelectedSuite(detail);
      setLastRun(null);
      setRunDiff(null);
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
      setRunDiff(null);
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
        cron_expression: newSchedule.cron_expression.trim(),
        webhook_url: newSchedule.webhook_url.trim(),
        scoring: newSchedule.scoring,
        enabled: true,
      });
      setNewSchedule({ suite_id: "", interval_hours: 24, cron_expression: "", webhook_url: "", scoring: "rules" });
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

  async function handleCreateAlert(e) {
    e.preventDefault();
    if (!newAlert.suite_id) return;
    setBusy(true);
    setError("");
    try {
      await createEvalAlert({
        suite_id: Number(newAlert.suite_id),
        min_pass_rate: Number(newAlert.min_pass_rate),
        drop_points: Number(newAlert.drop_points),
        webhook_url: newAlert.webhook_url.trim(),
        pagerduty_routing_key: newAlert.pagerduty_routing_key.trim(),
        opsgenie_api_key: newAlert.opsgenie_api_key.trim(),
        email_to: newAlert.email_to.trim(),
        use_workspace_slack: !!newAlert.use_workspace_slack,
      });
      setNewAlert({
        suite_id: "",
        min_pass_rate: 80,
        drop_points: 10,
        webhook_url: "",
        pagerduty_routing_key: "",
        opsgenie_api_key: "",
        email_to: "",
        use_workspace_slack: true,
      });
      await load();
    } catch (err) {
      setError(err.message || "Create alert failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleLoadDiff() {
    if (!lastRun?.id) return;
    setBusy(true);
    setError("");
    try {
      const diff = await getEvalRunDiff(lastRun.id);
      setRunDiff(diff);
    } catch (err) {
      setError(err.message || "Diff failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleEstimateCost(datasetId) {
    setBusy(true);
    setError("");
    try {
      const est = await estimateFineTuneCost(datasetId);
      setCostEstimate(est);
    } catch (err) {
      setError(err.message || "Estimate failed");
    } finally {
      setBusy(false);
    }
  }

  const diffStatusStyle = {
    regressed: "border-red-200 bg-red-50/60",
    improved: "border-emerald-200 bg-emerald-50/60",
    unchanged: "border-black/5 bg-white/50",
    new: "border-blue-200 bg-blue-50/40",
    removed: "border-amber-200 bg-amber-50/40",
  };

  async function handleCreateFromTemplate(e) {
    e.preventDefault();
    if (!templatePick.template_id || !templatePick.assistant_id) return;
    setBusy(true);
    setError("");
    try {
      await createSuiteFromTemplate({
        template_id: templatePick.template_id,
        assistant_id: templatePick.assistant_id,
      });
      setTemplatePick({ template_id: "", assistant_id: "" });
      await load();
    } catch (err) {
      setError(err.message || "Template import failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateAbRoute(e) {
    e.preventDefault();
    if (!newAbRoute.base_model.trim() || !newAbRoute.variant_model.trim()) return;
    setBusy(true);
    try {
      await createAbRoute({
        base_model: newAbRoute.base_model.trim(),
        variant_model: newAbRoute.variant_model.trim(),
        variant_traffic_pct: Number(newAbRoute.variant_traffic_pct) || 50,
      });
      setNewAbRoute({ base_model: "", variant_model: "", variant_traffic_pct: 50 });
      await load();
    } catch (err) {
      setError(err.message || "A/B route failed");
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
      setNewDataset({
        name: "",
        system:
          "You are a precise assistant. Lead with the answer, then short supporting bullets. If information is missing, say so.",
        user: "",
        assistant: "",
      });
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
    return <WorkspacePageShell loading loadingMessage="Loading evaluation…" />;
  }

  const evalTabs = [
    { id: "benchmark", label: "Benchmarks", count: suites.length },
    { id: "compare", label: "Compare" },
    { id: "trends", label: "Trends" },
    { id: "drift", label: "Drift radar" },
    { id: "schedules", label: "Schedules", count: schedules.length },
    { id: "alerts", label: "Alerts", count: alerts.length },
    { id: "finetune", label: "Fine-tune", count: datasets.length },
  ];

  return (
    <WorkspacePageShell user={user}>
          <WorkspaceHero
            eyebrow="Quality"
            title="Evaluation &"
            titleHighlight="fine-tune"
            description="Benchmark assistants with test cases and launch OpenAI fine-tuning jobs from training datasets."
            badge={readOnly ? undefined : <span className="workspace-badge-live">Quality lab</span>}
          >
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <WorkspaceStatCard label="Suites" value={String(suites.length)} hint="Benchmark collections" />
              <WorkspaceStatCard label="Schedules" value={String(schedules.length)} hint="Automated runs" />
              <WorkspaceStatCard label="Datasets" value={String(datasets.length)} hint="Fine-tune training" />
              <WorkspaceStatCard
                label="Jobs"
                value={String(jobs.length)}
                hint={quotas ? `Eval used: ${quotas.eval_runs_this_month || 0}` : "Fine-tune jobs"}
              />
            </div>
          </WorkspaceHero>

          <WorkspaceTabs tabs={evalTabs} active={tab} onChange={setTab} className="mt-8" />

          {error && <WorkspaceAlert type="error" className="mt-4">{error}</WorkspaceAlert>}

          {tab === "benchmark" && (
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="workspace-panel rounded-[1.5rem] p-5"
              >
                <h2 className="text-lg font-semibold">Benchmark suites</h2>
                {loading ? (
                  <WorkspaceSkeletonList count={4} height="h-14" />
                ) : suites.length === 0 ? (
                  <WorkspaceEmpty
                    className="mt-4"
                    title="No benchmark suites yet"
                    description="Create a suite below or import from a template to start scoring."
                    icon="◎"
                  />
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
                  <form onSubmit={handleCreateFromTemplate} className="mt-6 space-y-3 border-t border-black/5 pt-5">
                    <h3 className="text-sm font-semibold">From template</h3>
                    <select
                      className="input-field w-full"
                      value={templatePick.template_id}
                      onChange={(e) => setTemplatePick((p) => ({ ...p, template_id: e.target.value }))}
                    >
                      <option value="">Industry template…</option>
                      {templates.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name} ({t.case_count} cases)
                        </option>
                      ))}
                    </select>
                    <select
                      className="input-field w-full"
                      value={templatePick.assistant_id}
                      onChange={(e) => setTemplatePick((p) => ({ ...p, assistant_id: e.target.value }))}
                      required={!!templatePick.template_id}
                    >
                      <option value="">Assistant…</option>
                      {assistants.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                    <button type="submit" disabled={busy || !templatePick.template_id} className="btn-primary disabled:opacity-50">
                      Create from template
                    </button>
                  </form>
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
                            <option value="rules">Rules (contains / exact / fuzzy)</option>
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
                      CSV columns: input, expected, match_type (contains|exact|fuzzy|regex|judge)
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
                        <button
                          type="button"
                          disabled={busy}
                          onClick={handleLoadDiff}
                          className="workspace-btn-ghost mt-2 !py-1 text-xs"
                        >
                          {runDiff ? "Refresh diff vs previous" : "Diff vs previous run"}
                        </button>
                      </div>
                    )}
                    {runDiff && (
                      <div className="mt-3 rounded-xl border border-black/5 bg-white/60 px-4 py-3 text-xs">
                        <p className="font-semibold text-neutral-800">
                          Run #{runDiff.current_run_id} vs #{runDiff.baseline_run_id}:{" "}
                          {runDiff.pass_rate_delta >= 0 ? "+" : ""}
                          {runDiff.pass_rate_delta}% pass rate
                        </p>
                        <p className="mt-1 text-neutral-500">
                          {runDiff.summary.regressed} regressed · {runDiff.summary.improved} improved ·{" "}
                          {runDiff.summary.unchanged} unchanged
                        </p>
                        <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">
                          {runDiff.items
                            .filter((i) => i.status === "regressed" || i.status === "improved")
                            .map((item) => (
                              <li
                                key={item.case_id}
                                className={`rounded border px-2 py-1 ${diffStatusStyle[item.status] || ""}`}
                              >
                                <span className="font-medium capitalize">{item.status}</span>: {item.input}
                              </li>
                            ))}
                        </ul>
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

          {tab === "trends" && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="workspace-panel mt-6 rounded-[1.5rem] p-5"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Quality trends</h2>
                  <p className="mt-1 text-sm text-neutral-500">Pass rate over time for benchmarks and comparisons.</p>
                </div>
                <select
                  className="input-field !w-auto text-sm"
                  value={trendSuiteId}
                  onChange={(e) => setTrendSuiteId(e.target.value)}
                >
                  <option value="">Select suite…</option>
                  {suites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="mt-6 grid gap-8 lg:grid-cols-2">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-700">Benchmark pass rate</h3>
                  <SuiteTrendChart points={suiteTrends} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-neutral-700">Comparison history</h3>
                  <ComparisonTrendChart series={comparisonTrends} />
                </div>
              </div>
            </motion.section>
          )}

          {tab === "drift" && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="workspace-panel mt-6 rounded-[1.5rem] p-5"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Prompt drift radar</h2>
                  <p className="mt-1 text-sm text-neutral-500">
                    Detect eval regressions and cases that flipped from pass to fail.
                  </p>
                </div>
                <select
                  className="input-field !w-auto text-sm"
                  value={trendSuiteId}
                  onChange={(e) => setTrendSuiteId(e.target.value)}
                >
                  <option value="">All suites</option>
                  {suites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
              {driftRadar ? (
                <>
                  <div className="mt-6 grid gap-4 sm:grid-cols-3">
                    <WorkspaceStatCard label="Suites analyzed" value={driftRadar.suites_analyzed || 0} />
                    <WorkspaceStatCard label="Warnings" value={driftRadar.warning_count || 0} />
                    <WorkspaceStatCard label="Critical" value={driftRadar.critical_count || 0} />
                  </div>
                  <ul className="mt-6 space-y-3">
                    {(driftRadar.radar || []).length === 0 ? (
                      <li className="text-sm text-neutral-500">Need at least 2 eval runs per suite to detect drift.</li>
                    ) : (
                      driftRadar.radar.map((row) => (
                        <li
                          key={row.suite_id}
                          className={`rounded-xl border p-4 ${
                            row.severity === "critical"
                              ? "border-red-200 bg-red-50/80"
                              : row.severity === "warning"
                                ? "border-amber-200 bg-amber-50/80"
                                : "border-black/[0.06] bg-white/80"
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="font-semibold">{row.suite_name}</p>
                            <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                              {row.severity}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-neutral-600">
                            Pass rate {row.pass_rate}% ({row.delta >= 0 ? "+" : ""}
                            {row.delta}% vs baseline) · {row.regression_count} regression(s)
                          </p>
                          {row.regressions?.length > 0 && (
                            <ul className="mt-2 space-y-1 text-xs text-neutral-600">
                              {row.regressions.map((r, i) => (
                                <li key={i} className="rounded-lg bg-white/70 px-2 py-1.5">
                                  {(r.input || "").slice(0, 100)}
                                </li>
                              ))}
                            </ul>
                          )}
                        </li>
                      ))
                    )}
                  </ul>
                </>
              ) : (
                <p className="mt-6 text-sm text-neutral-500">Loading drift analysis…</p>
              )}
            </motion.section>
          )}

          {tab === "schedules" && (
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <motion.section className="workspace-panel rounded-[1.5rem] p-5">
                <h2 className="text-lg font-semibold">Scheduled runs</h2>
                <p className="mt-1 text-xs text-neutral-500">
                  Auto-run benchmarks on an interval or cron expression. Optional webhook on completion.
                </p>
                {quotas && (
                  <p className="mt-2 text-xs text-neutral-500">
                    Usage this month: {quotas.eval_runs_this_month}
                    {quotas.eval_runs_monthly_limit ? ` / ${quotas.eval_runs_monthly_limit} eval runs` : " eval runs"}
                    {" · "}
                    {quotas.finetune_jobs_this_month}
                    {quotas.finetune_jobs_monthly_limit
                      ? ` / ${quotas.finetune_jobs_monthly_limit} fine-tune jobs`
                      : " fine-tune jobs"}
                  </p>
                )}
                <ul className="mt-4 space-y-2">
                  {schedules.map((sched) => {
                    const suite = suites.find((s) => s.id === sched.suite_id);
                    return (
                      <li key={sched.id} className="workspace-list-row rounded-xl px-4 py-3 text-sm">
                        <p className="font-medium">
                          {suite?.name || `Suite #${sched.suite_id}`}
                          <span className="ml-2 text-xs font-normal text-neutral-500">
                            {sched.cron_expression
                              ? `cron: ${sched.cron_expression}`
                              : `every ${sched.interval_hours}h`}{" "}
                            · {sched.enabled ? "on" : "off"}
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
                      placeholder="Interval (hours, if no cron)"
                      value={newSchedule.interval_hours}
                      onChange={(e) => setNewSchedule((p) => ({ ...p, interval_hours: e.target.value }))}
                    />
                    <input
                      className="input-field w-full font-mono text-xs"
                      placeholder="Cron expression (optional, e.g. 0 9 * * *)"
                      value={newSchedule.cron_expression}
                      onChange={(e) => setNewSchedule((p) => ({ ...p, cron_expression: e.target.value }))}
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

          {tab === "alerts" && (
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <motion.section className="workspace-panel rounded-[1.5rem] p-5">
                <h2 className="text-lg font-semibold">Regression alerts</h2>
                <p className="mt-1 text-xs text-neutral-500">
                  Notify via workspace Slack (Settings), custom webhook, email, or on-call tools when pass rate drops.
                </p>
                <ul className="mt-4 space-y-2">
                  {alerts.map((a) => {
                    const suite = suites.find((s) => s.id === a.suite_id);
                    return (
                      <li key={a.id} className="workspace-list-row rounded-xl px-4 py-3 text-sm">
                        <p className="font-medium">
                          {suite?.name || `Suite #${a.suite_id}`}
                          <span className="ml-2 text-xs font-normal text-neutral-500">
                            min {a.min_pass_rate}% · drop {a.drop_points}pts · {a.enabled ? "on" : "off"}
                          </span>
                        </p>
                        <p className="mt-1 text-[11px] text-neutral-400">
                          {[
                            a.use_workspace_slack ? "workspace Slack" : null,
                            a.webhook_url ? "webhook" : null,
                            a.email_to ? `email ${a.email_to}` : null,
                            a.pagerduty_routing_key ? "PagerDuty" : null,
                          ]
                            .filter(Boolean)
                            .join(" · ") || "no channels"}
                        </p>
                        {!readOnly && (
                          <div className="mt-2 flex gap-2">
                            <button
                              type="button"
                              disabled={busy}
                              onClick={async () => {
                                await updateEvalAlert(a.id, { enabled: !a.enabled });
                                await load();
                              }}
                              className="workspace-btn-ghost !py-1 text-xs"
                            >
                              {a.enabled ? "Pause" : "Resume"}
                            </button>
                            <button
                              type="button"
                              disabled={busy}
                              onClick={async () => {
                                await deleteEvalAlert(a.id);
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
                  <h2 className="text-lg font-semibold">New alert</h2>
                  <form onSubmit={handleCreateAlert} className="mt-4 space-y-3">
                    <select
                      className="input-field w-full"
                      value={newAlert.suite_id}
                      onChange={(e) => setNewAlert((p) => ({ ...p, suite_id: e.target.value }))}
                      required
                    >
                      <option value="">Suite…</option>
                      {suites.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        min={0}
                        max={100}
                        className="input-field w-full"
                        placeholder="Min pass %"
                        value={newAlert.min_pass_rate}
                        onChange={(e) => setNewAlert((p) => ({ ...p, min_pass_rate: e.target.value }))}
                      />
                      <input
                        type="number"
                        min={1}
                        className="input-field w-full"
                        placeholder="Drop pts vs prev"
                        value={newAlert.drop_points}
                        onChange={(e) => setNewAlert((p) => ({ ...p, drop_points: e.target.value }))}
                      />
                    </div>
                    <label className="flex items-center gap-2 text-sm text-neutral-700">
                      <input
                        type="checkbox"
                        checked={!!newAlert.use_workspace_slack}
                        onChange={(e) => setNewAlert((p) => ({ ...p, use_workspace_slack: e.target.checked }))}
                      />
                      Use workspace Slack (Settings → Integrations)
                    </label>
                    <input
                      className="input-field w-full text-xs"
                      placeholder="Optional extra Slack / webhook URL"
                      value={newAlert.webhook_url}
                      onChange={(e) => setNewAlert((p) => ({ ...p, webhook_url: e.target.value }))}
                    />
                    <input
                      className="input-field w-full text-xs font-mono"
                      placeholder="PagerDuty routing key"
                      value={newAlert.pagerduty_routing_key}
                      onChange={(e) => setNewAlert((p) => ({ ...p, pagerduty_routing_key: e.target.value }))}
                    />
                    <input
                      className="input-field w-full text-xs font-mono"
                      placeholder="Opsgenie API key"
                      value={newAlert.opsgenie_api_key}
                      onChange={(e) => setNewAlert((p) => ({ ...p, opsgenie_api_key: e.target.value }))}
                    />
                    <input
                      className="input-field w-full text-xs"
                      placeholder="Email to (uses Gmail/SMTP from Settings → Integrations)"
                      value={newAlert.email_to}
                      onChange={(e) => setNewAlert((p) => ({ ...p, email_to: e.target.value }))}
                    />
                    <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
                      Create alert
                    </button>
                  </form>
                </motion.section>
              )}
            </div>
          )}

          {tab === "finetune" && (
            <div className="mt-6 grid gap-6 lg:grid-cols-3">
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
                              onClick={() => handleEstimateCost(d.id)}
                              className="workspace-btn-ghost !py-1.5 text-xs"
                            >
                              Estimate
                            </button>
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
                {costEstimate && (
                  <div className="mt-4 rounded-xl border border-black/5 bg-white/70 px-4 py-3 text-sm">
                    <p className="font-semibold">Cost estimate — dataset #{costEstimate.dataset_id}</p>
                    <p className="mt-1 text-neutral-600">
                      ~${costEstimate.estimated_cost_usd} USD (
                      {costEstimate.estimated_training_tokens.toLocaleString()} tokens ×{" "}
                      {costEstimate.assumed_epochs} epochs @ ${costEstimate.price_per_1m_tokens_usd}/1M)
                    </p>
                    <p className="mt-1 text-xs text-neutral-400">{costEstimate.disclaimer}</p>
                  </div>
                )}
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
                <h2 className="text-lg font-semibold">A/B model routing</h2>
                <p className="mt-1 text-xs text-neutral-500">
                  Split live assistant chat traffic between base and fine-tuned models.
                </p>
                <ul className="mt-3 space-y-2">
                  {abRoutes.map((r) => (
                    <li key={r.id} className="workspace-list-row rounded-xl px-4 py-3 text-xs">
                      <p className="font-medium">
                        {r.base_model} ↔ {r.variant_model}{" "}
                        <span className="text-neutral-500">({r.variant_traffic_pct}% variant)</span>
                      </p>
                      {!readOnly && (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={async () => {
                            await deleteAbRoute(r.id);
                            await load();
                          }}
                          className="workspace-btn-ghost workspace-btn-danger mt-2 !py-1"
                        >
                          Delete
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                {!readOnly && (
                  <form onSubmit={handleCreateAbRoute} className="mt-4 space-y-2 border-t border-black/5 pt-4">
                    <input
                      className="input-field w-full font-mono text-xs"
                      placeholder="Base model"
                      value={newAbRoute.base_model}
                      onChange={(e) => setNewAbRoute((p) => ({ ...p, base_model: e.target.value }))}
                    />
                    <input
                      className="input-field w-full font-mono text-xs"
                      placeholder="Fine-tuned variant model"
                      value={newAbRoute.variant_model}
                      onChange={(e) => setNewAbRoute((p) => ({ ...p, variant_model: e.target.value }))}
                    />
                    <input
                      type="number"
                      min={0}
                      max={100}
                      className="input-field w-full text-xs"
                      placeholder="Variant traffic %"
                      value={newAbRoute.variant_traffic_pct}
                      onChange={(e) => setNewAbRoute((p) => ({ ...p, variant_traffic_pct: e.target.value }))}
                    />
                    <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
                      Enable A/B route
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
    </WorkspacePageShell>
  );
}
