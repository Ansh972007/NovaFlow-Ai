"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { listAgentTools, runAgent } from "@/lib/api/agents";
import { listKnowledge } from "@/lib/api/knowledge";

const ease = [0.16, 1, 0.3, 1];

const TOOL_PRESETS = [
  { id: "summarize", label: "Summarize", desc: "Condense long text" },
  { id: "calculator", label: "Calculator", desc: "Math & expressions" },
  { id: "kb_search", label: "KB search", desc: "Query linked libraries" },
  { id: "translate_en", label: "Translate EN", desc: "Translate to English" },
];

export default function AgentsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [tools, setTools] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [selectedTools, setSelectedTools] = useState(["summarize"]);
  const [knowledgeId, setKnowledgeId] = useState("");
  const [system, setSystem] = useState("You are a capable NovaFlow agent. Use tool results when helpful.");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getUserInfo()
      .then((u) => {
        if (!u) {
          router.replace("/login");
          return;
        }
        setUser(u);
        return Promise.all([
          listAgentTools().catch(() => []),
          listKnowledge({ pageSize: 50 }).catch(() => ({ items: [] })),
        ]);
      })
      .then((res) => {
        if (!res) return;
        const [toolList, kb] = res;
        setTools(toolList || []);
        setKnowledge(kb?.items || kb?.data || []);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  const toggleTool = useCallback((id) => {
    setSelectedTools((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id].slice(0, 5)));
  }, []);

  async function handleRun() {
    if (!input.trim() || busy) return;
    setBusy(true);
    setError("");
    setOutput("");
    try {
      const res = await runAgent({
        input: input.trim(),
        tools: selectedTools,
        knowledge_id: knowledgeId ? Number(knowledgeId) : undefined,
        system,
      });
      setOutput(res?.output || "(no output)");
    } catch (e) {
      setError(e.message || "Agent run failed");
    } finally {
      setBusy(false);
    }
  }

  const displayTools = tools.length
    ? tools.map((t) => ({ id: t.id, label: t.id, desc: t.description || t.id }))
    : TOOL_PRESETS;

  return (
    <WorkspacePageShell user={user} maxWidth="max-w-6xl">
      <WorkspaceHero
        eyebrow="Agents"
        title="Tool-augmented"
        titleHighlight="runs"
        description="Chain built-in tools — calculator, KB search, summarize, translate — without building a workflow."
        badge={<span className="workspace-badge-live">{selectedTools.length} tools active</span>}
        actions={
          <Link href="/workflows" className="workspace-btn-ghost shrink-0">
            Open workflow studio
          </Link>
        }
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <WorkspaceStatCard label="Tools available" value={String(displayTools.length)} hint="Select up to 5 per run" />
          <WorkspaceStatCard label="Knowledge bases" value={String(knowledge.length)} hint="For kb_search tool" />
          <WorkspaceStatCard label="Selected" value={String(selectedTools.length)} hint={selectedTools.join(", ") || "None"} />
        </div>
      </WorkspaceHero>

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ease }}
          className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
        >
          <p className="workspace-section-label">Configure run</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">Agent input</h2>

          <div className="mt-5">
            <p className="text-xs font-semibold text-neutral-600">Tools</p>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {displayTools.map((t) => {
                const active = selectedTools.includes(t.id);
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => toggleTool(t.id)}
                    className={`setup-template-card ${active ? "setup-template-card--active" : ""}`}
                  >
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border ${
                        active ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-300 bg-white"
                      }`}
                    >
                      {active && (
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <path d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-neutral-900">{t.label || t.id}</span>
                      <span className="block truncate text-xs text-neutral-500">{t.desc}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {knowledge.length > 0 && selectedTools.includes("kb_search") && (
            <label className="mt-5 block text-sm font-medium">
              Knowledge base
              <select
                value={knowledgeId}
                onChange={(e) => setKnowledgeId(e.target.value)}
                className="input-field mt-1.5 w-full"
              >
                <option value="">Select knowledge base</option>
                {knowledge.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="mt-5 block text-sm font-medium">
            System prompt
            <textarea
              value={system}
              onChange={(e) => setSystem(e.target.value)}
              rows={2}
              className="input-field mt-1.5 w-full resize-none text-sm"
            />
          </label>

          <label className="mt-5 block text-sm font-medium">
            Input
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={6}
              placeholder="Ask the agent or paste text to process…"
              className="input-field mt-1.5 w-full resize-none text-sm"
            />
          </label>

          {error && <WorkspaceAlert type="error" className="mt-4">{error}</WorkspaceAlert>}

          <button
            type="button"
            onClick={handleRun}
            disabled={busy || !input.trim()}
            className="btn-primary mt-5 w-full disabled:opacity-50 sm:w-auto"
          >
            {busy ? "Running…" : "Run agent"}
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.06, ease }}
          className="workspace-panel flex min-h-[420px] flex-col rounded-[1.75rem] p-6 sm:p-7"
        >
          <p className="workspace-section-label">Response</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">Agent output</h2>

          {!output && !busy ? (
            <div className="workspace-empty mt-6 flex flex-1 flex-col items-center justify-center rounded-xl p-8 text-center">
              <div className="workspace-icon-tile h-12 w-12">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <rect x="4" y="8" width="16" height="12" rx="2" />
                  <path d="M9 8V6a3 3 0 0 1 6 0v2" />
                </svg>
              </div>
              <p className="mt-4 font-semibold text-neutral-900">Ready to run</p>
              <p className="mt-1 max-w-xs text-sm text-neutral-500">
                Select tools, enter input, and run to see results here.
              </p>
            </div>
          ) : busy ? (
            <div className="mt-6 flex flex-1 flex-col items-center justify-center gap-3">
              <div className="relative flex h-10 w-10 items-center justify-center">
                <div className="chat-empty-ring absolute inset-0 rounded-lg" />
                <div className="h-8 w-8 animate-pulse rounded-md bg-neutral-900/90" />
              </div>
              <p className="text-sm text-neutral-500">Agent is thinking…</p>
            </div>
          ) : (
            <div className="workspace-output-panel mt-5 flex-1">
              <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Output</p>
              <pre className="whitespace-pre-wrap">{output}</pre>
            </div>
          )}
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.15, ease }}
        className="workspace-panel mt-6 rounded-[1.75rem] p-5 text-sm text-neutral-600"
      >
        <p className="font-semibold text-neutral-900">Workflow integration</p>
        <p className="mt-1 leading-relaxed">
          Add an <strong>Agent</strong> node in the workflow builder to run the same tools inside automated pipelines.
          Pair with a <strong>Human</strong> node for review gates.
        </p>
      </motion.div>
    </WorkspacePageShell>
  );
}
