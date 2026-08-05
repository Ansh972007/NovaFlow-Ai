"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import SimpleMarkdown from "./SimpleMarkdown";

const DEFAULT_SUGGESTIONS = [
  "Summarize my documents",
  "Write a short email",
  "Explain step by step",
  "What can you do?",
];

const RAG_SUGGESTIONS = [
  "What do my documents say about this?",
  "Cite the key policy points",
  "Summarize the knowledge base",
  "Find contradictions if any",
];

const GOAL_CATEGORIES = [
  {
    label: "Support bot",
    prompt: "Build a telegram support bot that answers from knowledge",
  },
  {
    label: "Email digest",
    prompt: "Create a weekly email digest from my documents",
  },
  {
    label: "GitHub triage",
    prompt: "Build a GitHub issue triage workflow",
  },
  {
    label: "Knowledge Q&A",
    prompt: "What do my documents say about this?",
  },
  {
    label: "Custom agent",
    prompt: "Create a multi-agent research supervisor that asks me before acting",
  },
];

const COMPOSER_SUGGESTIONS = GOAL_CATEGORIES.map((c) => c.prompt);

const STATUS_STEPS = [
  { id: "draft", label: "Draft", match: ["pending_approval", "planning", "compiled", "compiled_draft"] },
  { id: "creds", label: "Credentials", match: ["needs_credentials"] },
  { id: "approved", label: "Approved", match: ["approved"] },
  { id: "tested", label: "Tested", match: ["tested", "test_failed"] },
  { id: "deployed", label: "Deployed", match: ["deployed", "done"] },
];

function latestAiosState(messages) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const ev = messages[i]?.event;
    if (!ev?.type?.startsWith?.("aios_")) continue;
    return ev;
  }
  return null;
}

function statusIndexFromEvent(ev) {
  if (!ev) return -1;
  const data = ev.data || {};
  const status = String(data.status || "");
  if (ev.type === "aios_deploy" && data.workflow_id) return 4;
  if (ev.type === "aios_credentials_needed" || (data.missing_credentials || []).length) return 1;
  if (ev.type === "aios_test_report") return 3;
  if (ev.type === "aios_approved") return 2;
  if (STATUS_STEPS[4].match.includes(status)) return 4;
  if (STATUS_STEPS[3].match.includes(status)) return 3;
  if (STATUS_STEPS[2].match.includes(status)) return 2;
  if (STATUS_STEPS[0].match.includes(status) || ev.type === "aios_solution") return 0;
  if (ev.type === "aios_progress") {
    const next = data.next_action;
    if (next === "credentials") return 1;
    if (next === "approve") return 0;
    if (next === "test") return 2;
    if (next === "deploy") return 3;
    if (next === "done") return 4;
  }
  return 0;
}

function ForgeChips({ chips, actionBtn, primaryBtn, onSuggest, primary = false }) {
  return (
    <div className="flex flex-wrap gap-1.5 pt-1">
      {(chips || []).map((chip) => (
        <button
          key={chip}
          type="button"
          className={primary ? primaryBtn : actionBtn}
          onClick={() => onSuggest?.(chip)}
        >
          {chip.length > 42 ? `${chip.slice(0, 40)}…` : chip}
        </button>
      ))}
    </div>
  );
}

function ForgeToolCard({ data, actionBtn, onSuggest, list }) {
  const rows = list || (data.radar || []).slice(0, 8).map((row, i) => (
    `${row.suite_name || row.name || row.suite_id || i}: Δ ${row.delta ?? row.pass_rate_delta ?? "—"}%`
  ));
  return (
    <div className="mt-1 space-y-1.5">
      <p>{data.message}</p>
      {rows.length > 0 && (
        <ul className="max-h-32 list-none space-y-0.5 overflow-y-auto text-[10px] text-neutral-600">
          {rows.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
      <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
    </div>
  );
}

export default function ChatMessages({
  messages,
  streaming,
  error,
  assistantName,
  onSuggest,
  onRegenerate,
  onClearError,
  hasKnowledge = false,
}) {
  const bottomRef = useRef(null);
  const [copiedId, setCopiedId] = useState("");
  const [highlightCite, setHighlightCite] = useState(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: streaming ? "auto" : "smooth",
      block: "end",
    });
  }, [messages.length, streaming, error]);

  const showThinking =
    streaming && messages.length > 0 && messages[messages.length - 1]?.role === "user";

  const latestAios = latestAiosState(messages);
  const statusIdx = statusIndexFromEvent(latestAios);

  const suggestions = hasKnowledge
    ? [...COMPOSER_SUGGESTIONS.slice(0, 2), ...RAG_SUGGESTIONS.slice(0, 2)]
    : [...COMPOSER_SUGGESTIONS.slice(0, 3), ...DEFAULT_SUGGESTIONS.slice(0, 2)];

  async function copyText(id, text) {
    try {
      await navigator.clipboard.writeText(text || "");
      setCopiedId(id);
      setTimeout(() => setCopiedId(""), 1500);
    } catch {
      /* ignore */
    }
  }

  function jumpToCite(msgId, n) {
    setHighlightCite(`${msgId}:${n}`);
    const el = document.getElementById(`cite-${msgId}-${n}`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    setTimeout(() => setHighlightCite(null), 1800);
  }

  const primaryBtn =
    "rounded-full border border-neutral-900 bg-neutral-900 px-3 py-1 text-[10px] font-semibold text-white hover:bg-neutral-800";
  const actionBtn =
    "rounded-full border border-neutral-300 bg-white px-2.5 py-1 text-[10px] font-semibold text-neutral-800 hover:bg-neutral-50 disabled:opacity-40";

  function renderAiosCard(msg) {
    const ev = msg?.event || {};
    const t = ev.type || "";
    const data = ev.data || {};
    if (!t) return null;
    const label =
      t === "aios_solution"
        ? "Your automation plan"
        : t === "aios_credentials_needed"
          ? "Credentials needed"
          : t === "aios_credentials_saved"
            ? "Credentials saved"
            : t === "aios_approved"
              ? "Plan approved"
              : t === "aios_test_report"
                ? "Sandbox test report"
                : t === "aios_sandbox"
                  ? "Enterprise test suite"
                  : t === "aios_deploy"
                  ? "Deployed"
                  : t === "aios_cancelled"
                    ? "Plan cancelled"
                    : t === "aios_clarify"
                      ? "Quick questions"
                      : t === "aios_progress"
                        ? "Progress"
                        : t === "aios_hitl"
                          ? "Needs your approval"
                          : t === "aios_heal"
                            ? "Graph heal"
                            : t === "aios_capabilities"
                              ? "Capabilities"
                              : t === "aios_workflows"
                                ? "Your workflows"
                                : t === "aios_run_status"
                                  ? "Run status"
                                  : t === "aios_knowledge"
                                    ? "Knowledge"
                                    : t === "aios_memory"
                                      ? "Memory"
                                      : t === "aios_agent_progress"
                                        ? "Agent OS"
                                        : t === "aios_agent_result"
                                          ? "Agent result"
                                          : t === "aios_schedule"
                                            ? "Schedule"
                                            : t === "aios_compliance"
                                              ? "Compliance"
                                              : t === "aios_finops"
                                                ? "FinOps"
                                                : t === "aios_health"
                                                  ? "Workspace health"
                                                  : t === "aios_recommendation"
                                                    ? "Recommendations"
                                                    : t === "aios_export"
                                                      ? "Export"
                                                      : t === "aios_share"
                                                        ? "Share"
                                                        : t === "aios_meta"
                                                          ? "Conversation meta"
                                                          : t === "aios_audit"
                                                            ? "Audit trail"
                                                            : t === "aios_vault"
                                                              ? "Credential vault"
                                                              : t === "aios_integration"
                                                                ? "Integrations"
                                                                : t === "aios_denied"
                                                                  ? "Permission denied"
                                                                  : t === "aios_playbook"
                                                                    ? "Playbook"
                                                                    : t === "aios_suggest"
                                                                      ? "Next steps"
                                                                      : t === "aios_requirements"
                                                                        ? "Requirements"
                                                                        : t === "aios_fulfillment"
                                                                          ? "Fulfillment"
                                                                          : t === "aios_policy"
                                                                            ? "Policy"
                                                                            : t === "aios_powerhouse"
                                                                              ? "Chat Powerhouse"
                                                                              : t === "aios_diff"
                                                                                ? "Workflow Diff Studio"
                                                                                : t === "aios_versions"
                                                                                  ? "Version Time Machine"
                                                                                  : t === "aios_eval"
                                                                                    ? "Eval Command Center"
                                                                                    : t === "aios_receipt"
                                                                                      ? "Cost Receipt"
                                                                                      : t === "aios_debug"
                                                                                        ? "Live Run Debugger"
                                                                                        : t === "aios_kg"
                                                                                          ? "Knowledge Graph"
                                                                                          : t === "aios_collab"
                                                                                            ? "Collab War Room"
                                                                                            : t === "aios_incident"
                                                                                              ? "Incident Kill Switch"
                                                                                              : t === "aios_simulate"
                                                                                                ? "Simulation Lab"
                                                                                                : t === "aios_sla"
                                                                                                  ? "SLA Reliability"
                                                                                                  : t === "aios_change_request"
                                                                                                    ? "Change Request"
                                                                                                    : t === "aios_digest"
                                                                                                      ? "Action Digest"
                                                                                                      : t === "aios_autopilot"
                                                                                                        ? "Chat Autopilot"
                                                                                                        : t === "aios_forge"
                                                                                                          ? "Chat Forge"
                                                                                                          : t === "aios_drift"
                                                                                                            ? "Drift Radar"
                                                                                                            : t === "aios_ab"
                                                                                                              ? "A/B Router"
                                                                                                              : t === "aios_webhook"
                                                                                                                ? "Webhook Studio"
                                                                                                                : t === "aios_project"
                                                                                                                  ? "Project Packs"
                                                                                                                  : t === "aios_publish_scan"
                                                                                                                    ? "Publish Scan"
                                                                                                                    : t === "aios_reuse"
                                                                                                                      ? "Template Reuse"
                                                                                                                      : t === "aios_model_lab"
                                                                                                                        ? "Model Lab"
                                                                                                                        : t === "aios_ocr"
                                                                                                                          ? "OCR → Workflow"
                                                                                                                          : t === "aios_issue"
                                                                                                                            ? "Issue Bridge"
                                                                                                                            : t === "aios_csv"
                                                                                                                              ? "CSV Import"
                                                                                                                              : t === "aios_docs"
                                                                                                                                ? "Solution Docs"
                                                                                                                                : t === "aios_assert"
                                                                                                                                  ? "Solution Assertions"
                                                                                                                                  : "Composer event";
    const nodeTypes =
      data.node_types ||
      data.executable_preview?.meta?.node_types ||
      (Array.isArray(data.executable_preview?.nodes)
        ? data.executable_preview.nodes.map((n) => n.type).filter(Boolean)
        : []);
    const next = data.next_action;
    return (
      <div className="mb-2 rounded-xl border border-neutral-200 bg-neutral-50/90 p-3 text-xs text-neutral-800">
        <p className="font-semibold tracking-tight text-neutral-900">{label}</p>
        {t === "aios_clarify" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {(data.questions || []).map((q, i) => (
              <p key={i} className="text-neutral-600">
                {i + 1}. {q}
              </p>
            ))}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 42 ? `${chip.slice(0, 40)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_progress" && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(data.steps || []).map((s, i) => (
              <span
                key={s.id || i}
                className="rounded-full border border-neutral-200 bg-white px-2 py-0.5 text-[10px] font-medium text-neutral-700"
              >
                {i + 1}. {s.label}
              </span>
            ))}
            {data.recipe_name && <p className="w-full text-neutral-600">Recipe: {data.recipe_name}</p>}
            {data.express && (
              <p className="w-full text-neutral-600">
                Express lane
                {data.compose_ms != null ? ` · composed in ${(data.compose_ms / 1000).toFixed(2)}s` : ""}
              </p>
            )}
            {!data.express && data.compose_ms != null && (
              <p className="w-full text-neutral-600">Composed in {(data.compose_ms / 1000).toFixed(2)}s</p>
            )}
            {(data.knowledge_id || data.attachment_count) && (
              <p className="w-full text-neutral-600">
                {data.knowledge_id ? `Knowledge #${data.knowledge_id}` : null}
                {data.knowledge_id && data.attachment_count ? " · " : null}
                {data.attachment_count ? `${data.attachment_count} attachment(s)` : null}
              </p>
            )}
            <div className="flex w-full flex-wrap gap-1.5 pt-1">
              <button type="button" className={primaryBtn} onClick={() => onSuggest?.("approve")}>
                Approve
              </button>
              {data.next_action === "heal" && (
                <button type="button" className={actionBtn} onClick={() => onSuggest?.("heal")}>
                  Fix &amp; retest
                </button>
              )}
            </div>
          </div>
        )}
        {t === "aios_sandbox" && (
          <div className="mt-1 space-y-1.5">
            <p>
              Status: <span className="font-semibold">{data.status || "—"}</span>
              {data.passed != null ? ` · ${data.passed} passed` : ""}
              {data.failed != null ? ` · ${data.failed} failed` : ""}
              {data.warnings != null && data.warnings > 0 ? ` · ${data.warnings} warn` : ""}
              {data.total_ms != null ? ` · ${data.total_ms}ms` : ""}
              {data.compose_ms != null ? ` · compose ${data.compose_ms}ms` : ""}
            </p>
            {Array.isArray(data.checks) && data.checks.length > 0 && (
              <ul className="max-h-32 list-none space-y-0.5 overflow-y-auto text-[10px] text-neutral-700">
                {data.checks.map((c, i) => (
                  <li key={c.id || i} className="flex gap-1.5">
                    <span
                      className={
                        c.status === "passed"
                          ? "font-semibold text-emerald-700"
                          : c.status === "warn"
                            ? "font-semibold text-amber-700"
                            : "font-semibold text-red-700"
                      }
                    >
                      {c.status === "passed" ? "PASS" : c.status === "warn" ? "WARN" : "FAIL"}
                    </span>
                    <span>
                      {c.name}: {c.message}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.primary === "Approve" || data.status === "success") && (
                <button type="button" className={primaryBtn} onClick={() => onSuggest?.("approve")}>
                  Approve
                </button>
              )}
              {data.status !== "success" && (
                <button type="button" className={primaryBtn} onClick={() => onSuggest?.("heal")}>
                  Fix &amp; retest
                </button>
              )}
              <button type="button" className={actionBtn} onClick={() => onSuggest?.("retest")}>
                Retest
              </button>
              {data.status === "success" && (
                <button type="button" className={actionBtn} onClick={() => onSuggest?.("deploy")}>
                  Deploy
                </button>
              )}
            </div>
          </div>
        )}
        {t === "aios_hitl" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || data.reason || "Agent OS is waiting for you."}</p>
            <p className="text-neutral-500">Status: {data.status || "pending"}</p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              <button type="button" className={primaryBtn} onClick={() => onSuggest?.("continue")}>
                Continue
              </button>
              <button type="button" className={actionBtn} onClick={() => onSuggest?.("hitl reject")}>
                Reject
              </button>
            </div>
          </div>
        )}
        {t === "aios_heal" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || "Applied graph repairs."}</p>
            {(data.fixes || []).length > 0 && (
              <ul className="list-disc pl-4 text-[10px] text-neutral-600">
                {data.fixes.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            )}
            {data.status === "suggested" && (
              <button type="button" className={primaryBtn} onClick={() => onSuggest?.("heal")}>
                Heal & retest
              </button>
            )}
            {data.status === "ask" && (
              <button type="button" className={primaryBtn} onClick={() => onSuggest?.("heal again")}>
                Heal again
              </button>
            )}
          </div>
        )}
        {t === "aios_capabilities" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.title || "What Peak Chat can do"}</p>
            <ul className="list-disc pl-4 text-[10px] text-neutral-600">
              {(data.skills || []).map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
            {(data.cannot || []).length > 0 && (
              <p className="text-[10px] text-amber-800">Boundary: {(data.cannot || []).join(" ")}</p>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 42 ? `${chip.slice(0, 40)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_workflows" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.count ?? (data.workflows || []).length} workflow(s)</p>
            <ul className="max-h-36 space-y-1 overflow-y-auto">
              {(data.workflows || []).map((w) => (
                <li key={w.id} className="flex flex-wrap items-center gap-2">
                  <a className="underline" href={w.link || `/workflows/${w.id}`}>
                    {w.name || w.id}
                  </a>
                  <button
                    type="button"
                    className={actionBtn}
                    onClick={() => onSuggest?.(`Run workflow ${w.name || w.id}`)}
                  >
                    Run
                  </button>
                </li>
              ))}
            </ul>
            {(data.workflows || []).length > 0 && (
              <button type="button" className={primaryBtn} onClick={() => onSuggest?.("Run my last workflow")}>
                Run last workflow
              </button>
            )}
          </div>
        )}
        {t === "aios_run_status" && (
          <div className="mt-1 space-y-1.5">
            <p>
              Status: <span className="font-semibold">{data.status || "—"}</span>
              {data.workflow_name ? ` · ${data.workflow_name}` : ""}
            </p>
            {data.message && <p className="text-neutral-600">{data.message}</p>}
            {data.output && (
              <p className="max-h-24 overflow-y-auto whitespace-pre-wrap text-[10px] text-neutral-600">
                {String(data.output).slice(0, 400)}
              </p>
            )}
            {Array.isArray(data.steps) && data.steps.length > 0 && (
              <ul className="max-h-28 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
                {data.steps.slice(0, 12).map((step, i) => (
                  <li key={i}>
                    {typeof step === "string"
                      ? step
                      : `${step.label || step.name || step.id || "step"}${step.status ? ` (${step.status})` : ""}`}
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-2 pt-1">
              {data.links?.workflow && (
                <a className="underline" href={data.links.workflow}>
                  Open workflow
                </a>
              )}
              {data.status === "failed" || data.status === "error" ? (
                <button type="button" className={primaryBtn} onClick={() => onSuggest?.("heal")}>
                  Heal
                </button>
              ) : null}
            </div>
          </div>
        )}
        {t === "aios_knowledge" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || `Knowledge: ${data.status || "updated"}`}</p>
            {data.name && <p className="text-neutral-600">{data.name}</p>}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || ["Use knowledge", "List my workflows"]).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_memory" && (
          <div className="mt-1 space-y-1.5">
            <p>Last recipe: {data.last_recipe || "—"}</p>
            {data.chip && (
              <button type="button" className={primaryBtn} onClick={() => onSuggest?.(data.chip)}>
                {data.chip}
              </button>
            )}
          </div>
        )}
        {t === "aios_agent_progress" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || "Agent OS running…"}</p>
            {data.goal && <p className="text-neutral-600">{data.goal}</p>}
            {Array.isArray(data.tasks) && data.tasks.length > 0 && (
              <ul className="list-disc pl-4 text-[10px] text-neutral-600">
                {data.tasks.slice(0, 6).map((task, i) => (
                  <li key={task.id || i}>{task.title || task.id || String(task)}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {t === "aios_agent_result" && (
          <div className="mt-1 space-y-1.5">
            {data.status === "error" ? (
              <p className="text-amber-800">{data.output || "Agent failed."}</p>
            ) : (
              <p className="max-h-36 overflow-y-auto whitespace-pre-wrap text-[11px]">
                {data.output || "Agent finished."}
              </p>
            )}
            {data.run_id && <p className="text-[10px] text-neutral-500">Run: {data.run_id}</p>}
          </div>
        )}
        {t === "aios_schedule" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || `Schedules: ${data.count ?? (data.schedules || []).length}`}</p>
            {data.cron_expression && (
              <p className="text-neutral-600">
                Cron: {data.cron_expression}
                {data.workflow_name ? ` · ${data.workflow_name}` : ""}
              </p>
            )}
            <ul className="max-h-36 space-y-1 overflow-y-auto text-[10px] text-neutral-600">
              {(data.schedules || []).slice(0, 10).map((s) => (
                <li key={s.id}>
                  #{s.id} {s.workflow_name || s.workflow_id} · {s.cron_expression}
                  {s.enabled ? "" : " (paused)"}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || ["List schedules"]).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 42 ? `${chip.slice(0, 40)}…` : chip}
                </button>
              ))}
              {data.links?.schedules && (
                <a className="underline" href={data.links.schedules}>
                  Open schedules
                </a>
              )}
            </div>
          </div>
        )}
        {t === "aios_compliance" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.title || "Compliance"}</p>
            <p className="text-neutral-600">
              Status: {data.compliance_status || data.posture || "—"}
              {data.audit_events != null ? ` · ${data.audit_events} audit events` : ""}
              {data.failed_operations != null ? ` · ${data.failed_operations} failed` : ""}
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_finops" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.title || "FinOps"}</p>
            <pre className="max-h-28 overflow-y-auto whitespace-pre-wrap text-[10px] text-neutral-600">
              {JSON.stringify(data.summary || {}, null, 0).slice(0, 500)}
            </pre>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_health" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.title || "Workspace health"}</p>
            <p>
              Posture: <span className="font-semibold">{data.posture || "—"}</span>
              {data.open_recommendations != null ? ` · ${data.open_recommendations} open recs` : ""}
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_recommendation" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || `${data.count ?? 0} recommendation(s)`}</p>
            <ul className="max-h-36 space-y-1 overflow-y-auto text-[10px] text-neutral-600">
              {(data.recommendations || []).slice(0, 8).map((r) => (
                <li key={r.id}>
                  [{r.severity}] {r.title}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 48 ? `${chip.slice(0, 46)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_export" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || `Export (${data.format || "markdown"})`}</p>
            {data.content && (
              <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-2 text-[10px] text-neutral-700">
                {String(data.content).slice(0, 4000)}
              </pre>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_share" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || "Share link created."}</p>
            {data.path && (
              <a className="underline break-all" href={data.path}>
                {data.path}
              </a>
            )}
            <p className="text-[10px] text-neutral-500">
              {data.permission} · expires {data.expires_at || "—"}
            </p>
          </div>
        )}
        {t === "aios_meta" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || data.title || "Updated."}</p>
            {data.summary && (
              <p className="max-h-28 overflow-y-auto whitespace-pre-wrap text-[11px] text-neutral-600">
                {data.summary}
              </p>
            )}
            {(data.tags || []).length > 0 && (
              <div className="flex flex-wrap gap-1">
                {data.tags.map((tag) => (
                  <span key={tag} className="rounded-full border border-neutral-200 bg-white px-2 py-0.5 text-[10px]">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
        {t === "aios_audit" && (
          <div className="mt-1 space-y-1.5">
            <p>
              {data.title || "Audit"} · {data.count ?? 0} event(s)
            </p>
            <ul className="max-h-36 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.entries || []).slice(0, 12).map((e, i) => (
                <li key={i}>
                  {e.created_at || ""} {e.action} {e.success === false ? "(fail)" : ""}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_vault" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || "Vault posture"}</p>
            {(data.missing || []).length > 0 && (
              <p className="text-amber-800">Missing: {data.missing.join(", ")}</p>
            )}
            {data.categories && (
              <p className="text-[10px] text-neutral-600">
                Categories:{" "}
                {Object.entries(data.categories)
                  .map(([k, v]) => `${k} (${v})`)
                  .join(", ")}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              <a className={`${actionBtn} inline-flex items-center`} href={data.credentials_url || "/credentials"}>
                Credentials
              </a>
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_integration" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || data.title || "Integrations"}</p>
            <ul className="text-[10px] text-neutral-600">
              {(data.channels || []).map((c) => (
                <li key={c.name}>
                  {c.name}: {c.configured ? "configured" : "not set"}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_denied" && (
          <div className="mt-1 space-y-1.5">
            <p className="text-amber-900">{data.message || "Permission denied."}</p>
            <p className="text-[10px] text-neutral-500">Required: {data.required_role || "editor"}</p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_playbook" && (
          <div className="mt-1 space-y-1.5">
            <p className="font-medium">{data.title || "Playbook"}</p>
            {data.summary && <p className="text-neutral-600">{data.summary}</p>}
            {Array.isArray(data.steps) && data.steps.length > 0 && (
              <ol className="list-decimal space-y-0.5 pl-4 text-[10px] text-neutral-600">
                {data.steps.map((s) => (
                  <li key={s.id || s.label}>{s.label}</li>
                ))}
              </ol>
            )}
            {(data.playbooks || []).length > 0 && (
              <ul className="space-y-1 text-[10px] text-neutral-600">
                {data.playbooks.map((p) => (
                  <li key={p.id}>{p.title}</li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={primaryBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 42 ? `${chip.slice(0, 40)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_suggest" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || "Turn this into a workflow?"}</p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || ["Build a workflow for this", "What can you do?"]).map((chip) => (
                <button key={chip} type="button" className={primaryBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 48 ? `${chip.slice(0, 46)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_requirements" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || data.title || "Requirements"}</p>
            {data.requirement && (
              <ul className="text-[10px] text-neutral-600">
                <li>Field: {data.requirement.field}</li>
                <li>Trigger: {data.requirement.trigger}</li>
                <li>Data: {data.requirement.data}</li>
                <li>Output: {data.requirement.output}</li>
                {data.requirement.sla && <li>SLA: {data.requirement.sla}</li>}
              </ul>
            )}
            {data.progress && <p className="text-[10px] text-neutral-500">Progress {data.progress}</p>}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || ["Fulfill these requirements"]).map((chip) => (
                <button key={chip} type="button" className={primaryBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 42 ? `${chip.slice(0, 40)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_fulfillment" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || data.title || "Fulfillment"}</p>
            <p className="text-[10px] text-neutral-500">Progress {data.progress || "—"}</p>
            <ul className="max-h-36 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.checklist || []).map((c) => (
                <li key={c.id} className={c.done ? "text-neutral-900" : ""}>
                  {c.done ? "✓" : "○"} {c.label}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || ["approve", "deploy"]).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_policy" && (
          <div className="mt-1 space-y-1.5">
            <p className={data.status === "denied" ? "text-amber-900" : ""}>
              {data.message || data.title || "Policy"}
            </p>
            {(data.policies || []).length > 0 && (
              <ul className="max-h-28 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
                {data.policies.map((p, i) => (
                  <li key={i}>
                    {p.rule_key} ({p.severity})
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_powerhouse" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || data.title || "Chat Powerhouse"}</p>
            <ul className="max-h-40 list-none space-y-1 overflow-y-auto text-[10px] text-neutral-700">
              {(data.tools || []).map((tool) => (
                <li key={tool.id} className="flex items-center justify-between gap-2 border-b border-neutral-100 py-0.5">
                  <span className="font-medium">{tool.title}</span>
                  <button type="button" className={actionBtn} onClick={() => onSuggest?.(tool.chip)}>
                    Open
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).slice(0, 6).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 36 ? `${chip.slice(0, 34)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_diff" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || `${data.from_label || "from"} → ${data.to_label || "to"}`}</p>
            {data.summary && (
              <p className="text-[10px] text-neutral-600">
                +{data.summary.nodes_added || 0}/−{data.summary.nodes_removed || 0} nodes · ~{data.summary.nodes_changed || 0}{" "}
                changed
              </p>
            )}
            {(data.nodes_added || []).length > 0 && (
              <p className="text-[10px]">Added: {(data.nodes_added || []).map((n) => n.id || n.label).join(", ")}</p>
            )}
            {data.markdown && (
              <pre className="max-h-28 overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-2 text-[10px] text-neutral-600">
                {String(data.markdown).slice(0, 2000)}
              </pre>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_versions" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || `${data.count ?? 0} version(s)`}</p>
            <ul className="max-h-32 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.versions || []).slice(0, 10).map((v) => (
                <li key={v.id}>
                  #{v.version_no} {v.name} {v.create_time || ""}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className={String(chip).toLowerCase().includes("restore") ? primaryBtn : actionBtn}
                  onClick={() => onSuggest?.(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_eval" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {data.last_run && (
              <p className="text-[10px] text-neutral-700">
                Last run: {data.last_run.pass_rate}% ({data.last_run.pass_count}/{data.last_run.total_count}) ·{" "}
                {data.last_run.avg_latency_ms}ms avg
              </p>
            )}
            {data.quick_matrix && (
              <p className="text-[10px]">
                Quick matrix: {data.quick_matrix.passed_fields}/{data.quick_matrix.field_count} fields ·{" "}
                {data.quick_matrix.status}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_receipt" && (
          <div className="mt-1 space-y-1.5">
            <p className={data.over_budget ? "text-amber-900" : ""}>{data.message}</p>
            <p className="text-[10px] text-neutral-600">
              Session ${Number(data.session_cost_usd || 0).toFixed(4)} / budget ${Number(data.budget_usd || 0).toFixed(2)} ·{" "}
              {data.turns || 0} turn(s)
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_debug" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {data.failed_node && (
              <p className="text-amber-800 text-[10px]">
                Failed node: {data.failed_node} ({data.failed_type})
              </p>
            )}
            <ul className="max-h-28 list-none space-y-0.5 overflow-y-auto text-[10px] text-neutral-600">
              {(data.timeline || []).slice(0, 12).map((step, i) => (
                <li key={i}>
                  [{step.status}] {step.node_id || step.node_type} {step.output_preview ? `— ${String(step.output_preview).slice(0, 80)}` : ""}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_kg" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <ul className="max-h-28 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.hits || []).slice(0, 6).map((h, i) => (
                <li key={i}>
                  {h.file_name}: {h.preview}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 40 ? `${chip.slice(0, 38)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_collab" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {data.share_path && (
              <a className="underline break-all" href={data.share_path}>
                {data.share_path}
              </a>
            )}
            {data.handoff_note && <p className="text-[10px] text-neutral-600">Handoff: {data.handoff_note}</p>}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_incident" && (
          <div className="mt-1 space-y-1.5">
            <p className={data.status === "executed" ? "text-amber-900" : ""}>{data.message}</p>
            {data.status === "executed" && (
              <p className="text-[10px]">
                Paused schedules: {data.paused_schedules ?? 0} · Stopped runs: {data.stopped_runs ?? 0}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className={String(chip).toLowerCase().includes("confirm") ? primaryBtn : actionBtn}
                  onClick={() => onSuggest?.(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_simulate" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <ul className="max-h-32 list-none space-y-0.5 overflow-y-auto text-[10px]">
              {(data.rows || []).map((row) => (
                <li key={row.field} className="flex gap-2">
                  <span
                    className={
                      row.status === "success" ? "font-semibold text-emerald-700" : "font-semibold text-red-700"
                    }
                  >
                    {row.status === "success" ? "PASS" : "FAIL"}
                  </span>
                  <span>
                    {row.field}: {row.fixture}
                  </span>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className={chip === "Approve" || chip === "Deploy" ? primaryBtn : actionBtn}
                  onClick={() => onSuggest?.(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_sla" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <p className="text-[10px] text-neutral-600">
              {data.run_count ?? 0} runs · {data.success_rate ?? 0}% · p95 {data.p95_latency_ms ?? 0}ms
            </p>
            {(data.top_failing_nodes || []).length > 0 && (
              <ul className="list-disc pl-4 text-[10px] text-neutral-600">
                {data.top_failing_nodes.map((n) => (
                  <li key={n.node}>
                    {n.node}: {n.count}
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_change_request" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {(data.notes || []).length > 0 && (
              <ul className="list-disc pl-4 text-[10px] text-neutral-600">
                {data.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
            {data.diff_summary && (
              <p className="text-[10px]">
                +{data.diff_summary.nodes_added || 0} nodes · +{data.diff_summary.edges_added || 0} edges
              </p>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className={String(chip).toLowerCase().includes("apply") ? primaryBtn : actionBtn}
                  onClick={() => onSuggest?.(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_digest" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <ul className="max-h-32 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.actions || []).map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 42 ? `${chip.slice(0, 40)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_autopilot" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <p className="text-[10px] text-neutral-600">
              Step {Number(data.step_index || 0) + 1}/{data.step_count ?? (data.steps || []).length ?? 0} ·{" "}
              {data.status || "running"}
            </p>
            <ul className="max-h-36 list-none space-y-1 overflow-y-auto text-[10px]">
              {(data.steps || []).map((step, i) => (
                <li
                  key={step.id || i}
                  className={
                    step.state === "current"
                      ? "font-semibold text-neutral-900"
                      : step.state === "done"
                        ? "text-emerald-700"
                        : "text-neutral-500"
                  }
                >
                  {step.state === "done" ? "✓ " : step.state === "current" ? "→ " : "○ "}
                  {step.label || step.chip}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className={String(chip).toLowerCase().includes("confirm") ? primaryBtn : actionBtn}
                  onClick={() => onSuggest?.(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_forge" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || data.title || "Chat Forge"}</p>
            <ul className="max-h-40 list-none space-y-1 overflow-y-auto text-[10px] text-neutral-700">
              {(data.tools || []).map((tool) => (
                <li key={tool.id} className="flex items-center justify-between gap-2 border-b border-neutral-100 py-0.5">
                  <span className="font-medium">{tool.title}</span>
                  <button type="button" className={actionBtn} onClick={() => onSuggest?.(tool.chip)}>
                    Open
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).slice(0, 6).map((chip) => (
                <button key={chip} type="button" className={actionBtn} onClick={() => onSuggest?.(chip)}>
                  {chip.length > 36 ? `${chip.slice(0, 34)}…` : chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_drift" && (
          <ForgeToolCard data={data} actionBtn={actionBtn} onSuggest={onSuggest} />
        )}
        {t === "aios_ab" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {data.picked && (
              <p className="text-[10px] text-neutral-600">
                Live pick: {data.picked.model} ({data.picked.variant})
              </p>
            )}
            <ul className="max-h-28 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.routes || []).slice(0, 6).map((r) => (
                <li key={r.id}>
                  {r.base_model} → {r.variant_model} ({r.variant_traffic_pct}%)
                </li>
              ))}
            </ul>
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_webhook" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <ul className="max-h-28 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.webhooks || []).slice(0, 8).map((w) => (
                <li key={w.id}>{w.direction}: {w.url}</li>
              ))}
            </ul>
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_project" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <ul className="max-h-28 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
              {(data.projects || []).slice(0, 8).map((p) => (
                <li key={p.id}>{p.name} ({p.status})</li>
              ))}
            </ul>
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_publish_scan" && (
          <div className="mt-1 space-y-1.5">
            <p className={data.status === "warn" ? "text-amber-900" : ""}>{data.message}</p>
            {(data.vulnerabilities || []).length > 0 && (
              <ul className="list-disc pl-4 text-[10px] text-amber-800">
                {data.vulnerabilities.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            )}
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_reuse" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {data.match && (
              <p className="text-[10px] text-neutral-600">
                {data.match.name || data.match.id} · {data.match.type}
              </p>
            )}
            <ForgeChips chips={data.chips} actionBtn={actionBtn} primaryBtn={primaryBtn} onSuggest={onSuggest} primary />
          </div>
        )}
        {t === "aios_model_lab" && (
          <ForgeToolCard data={data} actionBtn={actionBtn} onSuggest={onSuggest} list={(data.datasets || []).slice(0, 5).map((d) => d.name)} />
        )}
        {t === "aios_ocr" && (
          <ForgeToolCard
            data={data}
            actionBtn={actionBtn}
            onSuggest={onSuggest}
            list={(data.extracts || []).slice(0, 5).map((ex) => `${ex.file}: ${ex.preview}`)}
          />
        )}
        {t === "aios_issue" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {data.created?.html_url && (
              <a className="underline break-all text-[10px]" href={data.created.html_url}>
                {data.created.html_url}
              </a>
            )}
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_csv" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            <p className="text-[10px] text-neutral-600">
              {data.row_count ?? 0} rows · {data.eval_case_count ?? 0} eval cases
            </p>
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_docs" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message}</p>
            {data.markdown && (
              <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-2 text-[10px] text-neutral-600">
                {String(data.markdown).slice(0, 4000)}
              </pre>
            )}
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_assert" && (
          <div className="mt-1 space-y-1.5">
            <p className={data.status === "failed" ? "text-red-800" : "text-emerald-800"}>{data.message}</p>
            <ForgeChips chips={data.chips} actionBtn={actionBtn} onSuggest={onSuggest} />
          </div>
        )}
        {t === "aios_credentials_needed" && (
          <div className="mt-1 space-y-1.5">
            <p>
              {data.message ||
                `To continue I need: ${(data.missing || []).map((m) => String(m).replace(/_/g, " ")).join(", ") || "login details"}.`}
            </p>
            <a className="inline-flex underline" href={data.credentials_url || "/credentials"}>
              Open Credentials
            </a>
            <p className="text-[10px] text-neutral-500">
              Or paste here, e.g. smtp_password: your-app-password
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || []).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className={actionBtn}
                  onClick={() => {
                    if (String(chip).toLowerCase().includes("credential")) {
                      window.location.href = data.credentials_url || "/credentials";
                      return;
                    }
                    onSuggest?.(chip);
                  }}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_credentials_saved" && (
          <div className="mt-1 space-y-1.5">
            <p>{data.message || `Saved: ${(data.updated || []).join(", ") || "credentials"}`}</p>
            {(data.missing || []).length > 0 && (
              <p className="text-amber-800 text-[10px]">
                Still need: {(data.missing || []).map((m) => String(m).replace(/_/g, " ")).join(", ")}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {(data.chips || ["Approve", "Open Credentials"]).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className={String(chip).toLowerCase().includes("approve") ? primaryBtn : actionBtn}
                  onClick={() => onSuggest?.(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}
        {t === "aios_solution" && (
          <div className="mt-1 space-y-1.5">
            <p className="font-medium text-neutral-900">
              {data.friendly_title || data.display_recipe || "Your automation plan"}
            </p>
            {data.goal && (
              <p className="text-[11px] text-neutral-600 line-clamp-3">{String(data.goal).slice(0, 280)}</p>
            )}
            <p className="text-[10px] text-neutral-500">
              Status: {(data.status || "pending_approval").replace(/_/g, " ")}
            </p>
            {(data.missing_credentials || []).length > 0 && (
              <p className="text-amber-800">
                Still needed: {(data.missing_credentials || []).map((m) => String(m).replace(/_/g, " ")).join(", ")}
              </p>
            )}
            {data.message && <p className="text-amber-800">{data.message}</p>}
            <details className="text-[10px] text-neutral-500">
              <summary className="cursor-pointer font-semibold uppercase tracking-wide">Details</summary>
              {data.solution_id && <p className="mt-1 break-all">Plan id: {data.solution_id}</p>}
              {nodeTypes.length > 0 && <p>Steps: {nodeTypes.join(" → ")}</p>}
              {(data.recipe_name || data.recipe?.name) && (
                <p>Template: {data.display_recipe || data.recipe_name || data.recipe?.name}</p>
              )}
            </details>
            <div className="flex flex-wrap gap-1.5 pt-1">
              <button
                type="button"
                className={next === "approve" || !next ? primaryBtn : actionBtn}
                onClick={() => onSuggest?.("approve")}
              >
                Approve
              </button>
              <button type="button" className={actionBtn} onClick={() => onSuggest?.("run test")}>
                Test
              </button>
              <button
                type="button"
                className={next === "deploy" ? primaryBtn : actionBtn}
                onClick={() => onSuggest?.("deploy")}
              >
                Deploy
              </button>
              {(data.missing_credentials || []).length > 0 && (
                <a className={`${actionBtn} inline-flex items-center`} href="/credentials">
                  Credentials
                </a>
              )}
            </div>
          </div>
        )}
        {t === "aios_approved" && (
          <p className="mt-1">Solution {data.solution_id || ""} marked approved.</p>
        )}
        {t === "aios_test_report" && (
          <div className="mt-1 space-y-1.5">
            <p>
              Status: <span className="font-semibold">{data.status || "—"}</span>
              {data.passed != null ? ` · ${data.passed} passed` : ""}
              {data.failed != null ? ` · ${data.failed} failed` : ""}
              {data.total_ms != null
                ? ` · ${data.total_ms}ms`
                : data.total_latency_ms != null
                  ? ` · ${data.total_latency_ms}ms`
                  : ""}
              {data.node_count != null ? ` · ${data.node_count} nodes` : ""}
            </p>
            {Array.isArray(data.checks) && data.checks.length > 0 && (
              <ul className="max-h-28 list-none space-y-0.5 overflow-y-auto text-[10px] text-neutral-700">
                {data.checks.slice(0, 8).map((c, i) => (
                  <li key={c.id || i}>
                    <span className="font-semibold">{String(c.status || "").toUpperCase()}</span> {c.name}
                    {c.message ? `: ${c.message}` : ""}
                  </li>
                ))}
              </ul>
            )}
            {(!data.checks || !data.checks.length) && Array.isArray(data.logs) && data.logs.length > 0 && (
              <ul className="max-h-28 list-disc space-y-0.5 overflow-y-auto pl-4 text-[10px] text-neutral-600">
                {data.logs.slice(0, 12).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {data.status !== "success" && (
                <button type="button" className={primaryBtn} onClick={() => onSuggest?.("heal")}>
                  Fix &amp; retest
                </button>
              )}
              <button type="button" className={actionBtn} onClick={() => onSuggest?.("retest")}>
                Retest
              </button>
              <button
                type="button"
                className={data.status === "success" ? primaryBtn : actionBtn}
                onClick={() => onSuggest?.("deploy")}
              >
                Deploy
              </button>
            </div>
          </div>
        )}
        {t === "aios_deploy" && (
          <div className="mt-1 space-y-1">
            {data.message && <p>{data.message}</p>}
            <p>Workflow: {data.workflow_id || "—"}</p>
            <p>Agent: {data.agent_id || "—"}</p>
            {data.schedule_note && <p className="text-neutral-600">{data.schedule_note}</p>}
            <div className="flex flex-wrap gap-2 pt-1">
              {data.links?.workflow && (
                <a className="underline" href={data.links.workflow}>
                  Open workflow
                </a>
              )}
              {data.links?.schedules && (
                <a className="underline" href={data.links.schedules}>
                  Schedules
                </a>
              )}
              {data.links?.agent && (
                <a className="underline" href={`/developer?agent=${data.agent_id || ""}`}>
                  Open agent
                </a>
              )}
              {data.links?.docs && (
                <a className="underline" href={data.links.docs} target="_blank" rel="noreferrer">
                  Open docs
                </a>
              )}
            </div>
          </div>
        )}
        {t === "aios_cancelled" && <p className="mt-1">Pending plan cancelled.</p>}
      </div>
    );
  }

  const messageVariants = {
    hidden: { opacity: 0, y: 10, scale: 0.98 },
    visible: { opacity: 1, y: 0, scale: 1 },
  };

  return (
    <div className="chat-messages-scroll flex flex-1 flex-col overflow-y-auto">
      {statusIdx >= 0 && (
        <div className="sticky top-0 z-10 border-b border-neutral-200/70 bg-white/90 px-4 py-2 backdrop-blur-md sm:px-6">
          <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[10px] font-semibold tracking-wide text-neutral-400 uppercase">
              Composer
            </span>
            {STATUS_STEPS.map((step, i) => (
              <span
                key={step.id}
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  i <= statusIdx
                    ? "bg-neutral-900 text-white"
                    : "border border-neutral-200 bg-white text-neutral-400"
                }`}
              >
                {step.label}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8">
        {messages.length === 0 && !error ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-1 flex-col items-center justify-center py-8 text-center"
          >
            <div className="workspace-panel w-full max-w-lg rounded-[1.5rem] p-8 sm:p-10">
              <div className="relative mx-auto mb-6 flex h-20 w-20 items-center justify-center">
                <div className="chat-empty-ring-outer absolute inset-0 rounded-2xl" />
                <div className="chat-empty-ring absolute inset-1 rounded-2xl" />
                <motion.div
                  animate={{ scale: [1, 1.05, 1], rotate: [0, 2, -2, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                  className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-neutral-900 text-sm font-bold text-white shadow-xl"
                >
                  NF
                </motion.div>
              </div>

              <h2 className="text-2xl font-semibold tracking-tight text-neutral-900">
                {assistantName || "NovaFlow Assistant"}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-neutral-500">
                Build workflows, digests, bots, and agents — pick a category to start.
              </p>

              <div className="mt-8 flex flex-wrap justify-center gap-2.5">
                <motion.button
                  type="button"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSuggest?.("What can you do?")}
                  className="chat-suggest-chip rounded-full border border-neutral-900 bg-neutral-900 px-4 py-2.5 text-xs font-semibold text-white"
                >
                  What can you do?
                </motion.button>
                <motion.button
                  type="button"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.04 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSuggest?.("Workspace health")}
                  className="chat-suggest-chip rounded-full px-4 py-2.5 text-xs font-medium text-neutral-700"
                >
                  Workspace health
                </motion.button>
                <motion.button
                  type="button"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.06 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSuggest?.("Enterprise playbooks")}
                  className="chat-suggest-chip rounded-full px-4 py-2.5 text-xs font-medium text-neutral-700"
                >
                  Enterprise playbooks
                </motion.button>
                <motion.button
                  type="button"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.065 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSuggest?.("Show powerhouse")}
                  className="chat-suggest-chip rounded-full px-4 py-2.5 text-xs font-medium text-neutral-700"
                >
                  Show powerhouse
                </motion.button>
                <motion.button
                  type="button"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.07 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() =>
                    onSuggest?.("Capture requirements: onboard new hires with welcome email")
                  }
                  className="chat-suggest-chip rounded-full px-4 py-2.5 text-xs font-medium text-neutral-700"
                >
                  Capture requirements
                </motion.button>
                {GOAL_CATEGORIES.map((cat, i) => (
                  <motion.button
                    key={cat.label}
                    type="button"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.08 + i * 0.05 }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onSuggest?.(cat.prompt)}
                    className="chat-suggest-chip rounded-full px-4 py-2.5 text-xs font-medium text-neutral-700"
                  >
                    {cat.label}
                  </motion.button>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {suggestions.slice(0, 2).map((text) => (
                  <button
                    key={text}
                    type="button"
                    onClick={() => onSuggest?.(text)}
                    className="text-[11px] text-neutral-500 underline-offset-2 hover:underline"
                  >
                    {text.length > 48 ? `${text.slice(0, 46)}…` : text}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        ) : null}

        <AnimatePresence initial={false}>
          {messages.map((msg, idx) => {
            const isLastAssistant =
              msg.role === "assistant" &&
              !msg.streaming &&
              idx === messages.length - 1;
            return (
              <motion.div
                key={msg.id}
                variants={messageVariants}
                initial="hidden"
                animate="visible"
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-neutral-900 text-[10px] font-bold text-white shadow-md">
                    NF
                  </div>
                )}

                <div className={`max-w-[88%] sm:max-w-[80%] ${msg.role === "user" ? "text-right" : ""}`}>
                  {msg.role === "assistant" && (
                    <p className="mb-1.5 text-[10px] font-semibold tracking-[0.14em] text-neutral-400 uppercase">
                      {assistantName || "Assistant"}
                    </p>
                  )}
                  <div
                    className={`inline-block text-left text-sm leading-relaxed sm:text-[15px] ${
                      msg.role === "user"
                        ? "chat-bubble-user px-4 py-3"
                        : `chat-bubble-assistant px-4 py-3.5 text-neutral-800${msg.streaming ? " chat-bubble-streaming" : ""}`
                    }`}
                  >
                    {msg.event ? renderAiosCard(msg) : null}
                    {msg.role === "assistant" ? (
                      (() => {
                        const body = String(msg.content || "").trim();
                        const cardMsg = String(msg.event?.data?.message || "").trim();
                        // Avoid duplicate text under the card
                        const hideDup =
                          Boolean(msg.event) &&
                          body &&
                          (body === cardMsg ||
                            (cardMsg && body.includes(cardMsg.slice(0, Math.min(40, cardMsg.length)))));
                        if (hideDup && !msg.streaming) return null;
                        if (!body && !msg.streaming) return null;
                        return (
                      <SimpleMarkdown
                        text={
                          msg.content !== undefined && msg.content !== null
                            ? msg.content
                            : msg.streaming
                              ? ""
                              : "…"
                        }
                        onCiteClick={(n) => jumpToCite(msg.id, n)}
                      />
                        );
                      })()
                    ) : (
                      <p className="whitespace-pre-wrap break-words">
                        {msg.content || "…"}
                      </p>
                    )}
                    {msg.role === "user" && msg.attachments?.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {msg.attachments.map((a, i) => (
                          <span
                            key={`${a.file_name || a.name}-${i}`}
                            className="inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] text-indigo-800"
                          >
                            {a.file_name || a.name}
                          </span>
                        ))}
                      </div>
                    )}
                    {msg.streaming && !msg.content && (
                      <span className="inline-flex gap-1 py-1">
                        {[0, 1, 2].map((i) => (
                          <span
                            key={i}
                            className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
                            style={{ animationDelay: `${i * 120}ms` }}
                          />
                        ))}
                      </span>
                    )}
                    {msg.streaming && msg.content && (
                      <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-neutral-400 align-middle" />
                    )}

                    {msg.role === "assistant" && msg.reasoning && !msg.streaming && (
                      <details className="mt-2 border-t border-black/[0.05] pt-2">
                        <summary className="cursor-pointer text-[10px] font-semibold tracking-wide text-neutral-400 uppercase">
                          Reasoning
                        </summary>
                        <p className="mt-1 whitespace-pre-wrap text-[11px] text-neutral-500">
                          {msg.reasoning}
                        </p>
                      </details>
                    )}

                    {msg.role === "assistant" && msg.receipt && !msg.streaming && (
                      <div className="mt-3 space-y-2 border-t border-black/[0.06] pt-3 text-left">
                        {(msg.receipt.chunks?.length > 0 || msg.receipt.sources?.length > 0) && (
                          <div className="flex flex-wrap gap-1.5">
                            {(msg.receipt.chunks?.length
                              ? msg.receipt.chunks.slice(0, 8)
                              : (msg.receipt.sources || []).slice(0, 6).map((src, i) => ({
                                  n: i + 1,
                                  file_name: src,
                                  preview: src,
                                }))
                            ).map((c) => (
                              <button
                                key={`cite-${c.n}-${c.file_name}`}
                                type="button"
                                id={`cite-${msg.id}-${c.n}`}
                                onClick={() => jumpToCite(msg.id, c.n)}
                                className={`inline-flex max-w-[14rem] items-center truncate rounded-full border px-2.5 py-0.5 text-[10px] font-semibold transition-colors ${
                                  highlightCite === `${msg.id}:${c.n}`
                                    ? "border-emerald-400 bg-emerald-100 text-emerald-900"
                                    : "border-neutral-200 bg-neutral-50 text-neutral-700 hover:border-neutral-300"
                                }`}
                                title={c.preview || c.file_name}
                              >
                                [{c.n}] {c.file_name}
                              </button>
                            ))}
                            {msg.receipt.retrieval_method && (
                              <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                                {msg.receipt.retrieval_method}
                              </span>
                            )}
                          </div>
                        )}
                        {(msg.receipt.total_tokens != null ||
                          msg.receipt.est_cost_usd != null ||
                          msg.receipt.stopped) && (
                          <p className="text-[10px] text-neutral-400">
                            {msg.receipt.total_tokens != null ? `${msg.receipt.total_tokens} tokens` : null}
                            {msg.receipt.est_cost_usd != null
                              ? `${msg.receipt.total_tokens != null ? " · " : ""}~$${Number(msg.receipt.est_cost_usd).toFixed(5)}`
                              : null}
                            {msg.receipt.stopped
                              ? `${msg.receipt.total_tokens != null || msg.receipt.est_cost_usd != null ? " · " : ""}stopped`
                              : null}
                          </p>
                        )}
                        <details>
                          <summary className="cursor-pointer text-[11px] font-semibold tracking-wide text-neutral-500 uppercase">
                            AI Receipt
                          </summary>
                          <div className="mt-2 space-y-2 text-xs text-neutral-600">
                            <p>
                              <span className="font-medium text-neutral-800">Model:</span>{" "}
                              {msg.receipt.model || "—"}
                            </p>
                            {msg.receipt.ab_variant && (
                              <p>
                                <span className="font-medium text-neutral-800">A/B:</span>{" "}
                                {msg.receipt.ab_variant} ({msg.receipt.ab_model})
                              </p>
                            )}
                            <p>
                              <span className="font-medium text-neutral-800">RAG:</span>{" "}
                              {msg.receipt.rag_used
                                ? `${msg.receipt.source_count} source(s)`
                                : "Not used"}
                            </p>
                            {msg.receipt.chunks?.length > 0 && (
                              <ul className="space-y-1.5">
                                {msg.receipt.chunks.slice(0, 8).map((c, i) => (
                                  <li
                                    key={i}
                                    id={`cite-detail-${msg.id}-${c.n || i + 1}`}
                                    className={`rounded-lg px-2.5 py-2 text-[11px] leading-relaxed ${
                                      highlightCite === `${msg.id}:${c.n}`
                                        ? "bg-emerald-50 ring-1 ring-emerald-300"
                                        : "bg-neutral-50"
                                    }`}
                                  >
                                    <span className="font-medium">
                                      [{c.n || i + 1}] {c.file_name}
                                    </span>
                                    {c.score != null && (
                                      <span className="text-neutral-400"> · score {c.score}</span>
                                    )}
                                    {c.rrf != null && (
                                      <span className="text-neutral-400"> · rrf {c.rrf}</span>
                                    )}
                                    {c.method && (
                                      <span className="text-neutral-400"> · {c.method}</span>
                                    )}
                                    <p className="mt-0.5 text-neutral-500">{c.preview}</p>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </details>
                      </div>
                    )}
                  </div>

                  {msg.role === "assistant" && !msg.streaming && msg.content && (
                    <div className="mt-1.5 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => copyText(msg.id, msg.content)}
                        className="rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-[10px] font-semibold text-neutral-600 hover:bg-neutral-50"
                      >
                        {copiedId === msg.id ? "Copied" : "Copy"}
                      </button>
                      {isLastAssistant && !msg.event && (
                        <>
                          <button
                            type="button"
                            onClick={() => onSuggest?.("Build a workflow for this")}
                            className="rounded-full border border-neutral-900 bg-neutral-900 px-2.5 py-0.5 text-[10px] font-semibold text-white hover:bg-neutral-800"
                          >
                            Build a workflow for this
                          </button>
                          <button
                            type="button"
                            onClick={() => onSuggest?.("Enterprise playbooks")}
                            className="rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-[10px] font-semibold text-neutral-600 hover:bg-neutral-50"
                          >
                            Playbooks
                          </button>
                          <button
                            type="button"
                            onClick={() => onSuggest?.("What can you do?")}
                            className="rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-[10px] font-semibold text-neutral-600 hover:bg-neutral-50"
                          >
                            What can you do?
                          </button>
                        </>
                      )}
                      {isLastAssistant && onRegenerate && (
                        <button
                          type="button"
                          onClick={() => onRegenerate()}
                          disabled={streaming}
                          className="rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-[10px] font-semibold text-neutral-600 hover:bg-neutral-50 disabled:opacity-40"
                        >
                          Regenerate
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        <AnimatePresence>
          {showThinking && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex gap-3"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-neutral-200/80 bg-white/90 text-[10px] font-bold text-neutral-500 shadow-sm">
                NF
              </div>
              <div className="chat-bubble-assistant flex items-center gap-2 px-4 py-3.5 text-sm text-neutral-500">
                <span className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
                      style={{ animationDelay: `${i * 140}ms` }}
                    />
                  ))}
                </span>
                Composing…
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-xl border border-red-200/80 bg-red-50/95 px-4 py-3 text-sm text-red-700 shadow-sm"
          >
            <p>{error}</p>
            <div className="mt-2 flex gap-2">
              {onRegenerate && (
                <button
                  type="button"
                  onClick={() => {
                    onClearError?.();
                    onRegenerate();
                  }}
                  className="rounded-full border border-red-200 bg-white px-3 py-1 text-[11px] font-semibold text-red-700 hover:bg-red-50"
                >
                  Retry
                </button>
              )}
              {onClearError && (
                <button
                  type="button"
                  onClick={onClearError}
                  className="rounded-full px-3 py-1 text-[11px] font-semibold text-red-600/80 hover:text-red-800"
                >
                  Dismiss
                </button>
              )}
            </div>
          </motion.div>
        )}

        <div ref={bottomRef} className="h-px shrink-0" />
      </div>
    </div>
  );
}
