"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { getUserInfo } from "@/lib/api/auth";
import { listAgentTools, runAgent } from "@/lib/api/agents";
import { listKnowledge } from "@/lib/api/knowledge";

const ease = [0.16, 1, 0.3, 1];

const TOOL_PRESETS = [
  { id: "summarize", label: "Summarize" },
  { id: "calculator", label: "Calculator" },
  { id: "kb_search", label: "KB search" },
  { id: "translate_en", label: "Translate EN" },
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
        return Promise.all([listAgentTools().catch(() => []), listKnowledge({ pageSize: 50 }).catch(() => ({ items: [] }))]);
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

  const displayTools = tools.length ? tools : TOOL_PRESETS.map((t) => ({ id: t.id, description: t.label }));

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />
        <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
          <WorkspaceHero
            label="Agents"
            title="Tool-augmented runs"
            subtitle="Chain built-in tools — calculator, KB search, summarize, translate — without building a workflow."
          />

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ease }}
            className="workspace-panel mt-8 rounded-2xl p-6"
          >
            <p className="workspace-section-label">Tools</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {displayTools.map((t) => {
                const active = selectedTools.includes(t.id);
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => toggleTool(t.id)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                      active
                        ? "border-neutral-900 bg-neutral-900 text-white"
                        : "border-black/10 bg-white/80 text-neutral-600 hover:border-black/20"
                    }`}
                  >
                    {t.id}
                  </button>
                );
              })}
            </div>

            {knowledge.length > 0 && selectedTools.includes("kb_search") && (
              <label className="mt-5 block">
                <span className="text-xs font-semibold text-neutral-600">Knowledge base (for kb_search)</span>
                <select
                  value={knowledgeId}
                  onChange={(e) => setKnowledgeId(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
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

            <label className="mt-5 block">
              <span className="text-xs font-semibold text-neutral-600">System prompt</span>
              <textarea
                value={system}
                onChange={(e) => setSystem(e.target.value)}
                rows={2}
                className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              />
            </label>

            <label className="mt-5 block">
              <span className="text-xs font-semibold text-neutral-600">Input</span>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={5}
                placeholder="Ask the agent or paste text to process…"
                className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              />
            </label>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            <button type="button" onClick={handleRun} disabled={busy || !input.trim()} className="btn-primary mt-5">
              {busy ? "Running…" : "Run agent"}
            </button>

            {output && (
              <div className="mt-6 rounded-xl border border-black/[0.06] bg-white/60 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Output</p>
                <pre className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-neutral-800">{output}</pre>
              </div>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.15, ease }}
            className="mt-6 rounded-2xl border border-dashed border-black/10 bg-white/40 p-5 text-sm text-neutral-500"
          >
            <p className="font-semibold text-neutral-700">Workflow integration</p>
            <p className="mt-1">
              Add an <strong>Agent</strong> node in the workflow builder to run the same tools inside automated pipelines.
              Pair with a <strong>Human</strong> node for review gates.
            </p>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
