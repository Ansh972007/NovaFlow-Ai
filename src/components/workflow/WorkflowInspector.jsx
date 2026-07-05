"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { NODE_META } from "./WorkflowCanvas";

const ease = [0.16, 1, 0.3, 1];

export default function WorkflowInspector({
  tab,
  onTabChange,
  selected,
  nodes = [],
  edges = [],
  knowledgeBases,
  onUpdateNode,
  onConnect,
  onDisconnect,
  onDeleteNode,
  runInput,
  onRunInputChange,
  onRun,
  running,
  runResult,
  recentRuns,
  readOnly = false,
}) {
  const [connectTarget, setConnectTarget] = useState("");
  const [connectSource, setConnectSource] = useState("");

  const outgoing = selected
    ? edges.filter((e) => e.from === selected.id)
    : [];
  const incoming = selected
    ? edges.filter((e) => e.to === selected.id)
    : [];
  const otherNodes = selected
    ? nodes.filter((n) => n.id !== selected.id)
    : [];

  function nodeLabel(n) {
    return n.data?.label || n.data?.prompt?.slice(0, 24) || n.type;
  }
  const tabs = [
    { id: "configure", label: "Configure" },
    { id: "test", label: "Test run" },
    { id: "history", label: "History" },
  ];

  return (
    <aside className="workflow-studio-inspector flex h-full w-full flex-col border-l border-white/60 lg:w-[360px] xl:w-[380px]">
      <div className="shrink-0 border-b border-black/[0.05] p-3">
        <div className="flex gap-1 rounded-xl bg-white/50 p-1 ring-1 ring-black/[0.04]">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => onTabChange(t.id)}
              className={`flex-1 rounded-lg px-3 py-2.5 text-[11px] font-semibold transition-all ${
                tab === t.id
                  ? "bg-neutral-900 text-white shadow-md"
                  : "text-neutral-500 hover:bg-white/90 hover:text-neutral-900"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5 sm:p-6">
        <AnimatePresence mode="wait">
          {tab === "configure" && (
            <motion.div
              key="configure"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.25, ease }}
            >
              {!selected ? (
                <div className="workspace-empty flex flex-col items-center rounded-2xl px-6 py-12 text-center">
                  <div className="relative flex h-20 w-20 items-center justify-center">
                    <div className="absolute inset-0 animate-pulse rounded-full border-2 border-dashed border-neutral-300" />
                    <div className="h-12 w-12 rounded-full bg-neutral-100" />
                  </div>
                  <p className="mt-5 text-sm font-semibold text-neutral-800">Select a node</p>
                  <p className="mt-1 max-w-[200px] text-xs leading-relaxed text-neutral-500">
                    Tap a circular node on the canvas to configure it here.
                  </p>
                </div>
              ) : (
                <>
                  <div className="flex items-start gap-3 rounded-2xl border border-white/70 bg-white/60 p-3 backdrop-blur-sm">
                    <div
                      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 workflow-node-${selected.type}`}
                    >
                      <span className="text-[10px] font-bold uppercase text-neutral-500">
                        {selected.type.slice(0, 2)}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="workspace-section-label">Selected</p>
                      <h3 className="text-base font-semibold capitalize tracking-tight">
                        {NODE_META[selected.type]?.label || selected.type}
                      </h3>
                    </div>
                    {!readOnly && onDeleteNode && (
                      <button
                        type="button"
                        onClick={() => onDeleteNode(selected.id)}
                        className="workspace-btn-ghost workspace-btn-danger shrink-0 !px-2.5 !py-1.5 text-xs"
                      >
                        Delete
                      </button>
                    )}
                  </div>

                  {selected.type === "retrieve" && (
                    <label className="mt-6 block">
                      <span className="text-xs font-semibold text-neutral-600">Knowledge base</span>
                      <select
                        value={selected.data?.knowledge_id ?? ""}
                        onChange={(e) =>
                          onUpdateNode(selected.id, {
                            data: { knowledge_id: e.target.value ? Number(e.target.value) : null },
                          })
                        }
                        disabled={readOnly}
                        className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-neutral-900/10"
                      >
                        <option value="">Select library…</option>
                        {knowledgeBases.map((kb) => (
                          <option key={kb.id} value={kb.id}>
                            {kb.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}

                  {selected.type === "retrieve" && (
                    <label className="mt-4 block">
                      <span className="text-xs font-semibold text-neutral-600">Chunk limit</span>
                      <input
                        type="number"
                        min={1}
                        max={20}
                        value={selected.data?.limit ?? 5}
                        onChange={(e) =>
                          onUpdateNode(selected.id, {
                            data: { limit: Number(e.target.value) || 5 },
                          })
                        }
                        disabled={readOnly}
                        className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                      />
                    </label>
                  )}

                  {selected.type === "llm" && (
                    <label className="mt-6 block">
                      <span className="text-xs font-semibold text-neutral-600">System prompt</span>
                      <textarea
                        value={selected.data?.prompt || ""}
                        onChange={(e) => onUpdateNode(selected.id, { data: { prompt: e.target.value } })}
                        disabled={readOnly}
                        rows={8}
                        className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-neutral-900/10"
                        placeholder="Instructions for the LLM step…"
                      />
                    </label>
                  )}

                  {(selected.type === "trigger" || selected.type === "output") && (
                    <label className="mt-6 block">
                      <span className="text-xs font-semibold text-neutral-600">Label</span>
                      <input
                        value={selected.data?.label || ""}
                        onChange={(e) => onUpdateNode(selected.id, { data: { label: e.target.value } })}
                        disabled={readOnly}
                        className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        placeholder={selected.type === "trigger" ? "User input" : "Response"}
                      />
                    </label>
                  )}

                  {selected.type === "transform" && (
                    <label className="mt-6 block">
                      <span className="text-xs font-semibold text-neutral-600">Template</span>
                      <p className="mt-1 text-[11px] text-neutral-400">
                        Use {"{{input}}"}, {"{{retrieved}}"}, {"{{output}}"}, {"{{http}}"}
                      </p>
                      <textarea
                        value={selected.data?.template || ""}
                        onChange={(e) => onUpdateNode(selected.id, { data: { template: e.target.value } })}
                        disabled={readOnly}
                        rows={6}
                        className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm leading-relaxed"
                        placeholder="{{input}}"
                      />
                    </label>
                  )}

                  {selected.type === "condition" && (
                    <>
                      <label className="mt-6 block">
                        <span className="text-xs font-semibold text-neutral-600">Keyword (contains)</span>
                        <input
                          value={selected.data?.keyword || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { keyword: e.target.value } })}
                          disabled={readOnly}
                          className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                          placeholder="billing"
                        />
                      </label>
                      <label className="mt-4 block">
                        <span className="text-xs font-semibold text-neutral-600">Text when matched</span>
                        <textarea
                          value={selected.data?.then_text || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { then_text: e.target.value } })}
                          disabled={readOnly}
                          rows={3}
                          className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        />
                      </label>
                      <label className="mt-4 block">
                        <span className="text-xs font-semibold text-neutral-600">Text when not matched</span>
                        <textarea
                          value={selected.data?.else_text || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { else_text: e.target.value } })}
                          disabled={readOnly}
                          rows={3}
                          className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        />
                      </label>
                    </>
                  )}

                  {selected.type === "http" && (
                    <>
                      <label className="mt-6 block">
                        <span className="text-xs font-semibold text-neutral-600">URL</span>
                        <input
                          value={selected.data?.url || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { url: e.target.value } })}
                          disabled={readOnly}
                          className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                          placeholder="https://api.example.com/data?q={{input}}"
                        />
                      </label>
                      <label className="mt-4 block">
                        <span className="text-xs font-semibold text-neutral-600">Method</span>
                        <select
                          value={selected.data?.method || "GET"}
                          onChange={(e) => onUpdateNode(selected.id, { data: { method: e.target.value } })}
                          disabled={readOnly}
                          className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        >
                          <option value="GET">GET</option>
                          <option value="POST">POST</option>
                        </select>
                      </label>
                      <label className="mt-4 block">
                        <span className="text-xs font-semibold text-neutral-600">POST body (optional)</span>
                        <textarea
                          value={selected.data?.body || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { body: e.target.value } })}
                          disabled={readOnly}
                          rows={4}
                          className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        />
                      </label>
                    </>
                  )}

                  {selected.type === "loop" && (
                    <>
                      <label className="mt-6 block">
                        <span className="text-xs font-semibold text-neutral-600">Max items</span>
                        <input
                          type="number"
                          min={1}
                          max={20}
                          value={selected.data?.max || 5}
                          onChange={(e) => onUpdateNode(selected.id, { data: { max: Number(e.target.value) } })}
                          disabled={readOnly}
                          className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        />
                      </label>
                      <label className="mt-4 block">
                        <span className="text-xs font-semibold text-neutral-600">Per-item prompt</span>
                        <textarea
                          value={selected.data?.prompt || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { prompt: e.target.value } })}
                          disabled={readOnly}
                          rows={3}
                          className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                          placeholder="Process: {{item}}"
                        />
                      </label>
                    </>
                  )}

                  {selected.type === "parallel" && (
                    <label className="mt-6 block">
                      <span className="text-xs font-semibold text-neutral-600">Branches (comma-separated)</span>
                      <input
                        value={(selected.data?.branches || []).join(", ")}
                        onChange={(e) =>
                          onUpdateNode(selected.id, {
                            data: { branches: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) },
                          })
                        }
                        disabled={readOnly}
                        className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        placeholder="Summary, Key points, Actions"
                      />
                    </label>
                  )}

                  {selected.type === "human" && (
                    <>
                      <label className="mt-6 block">
                        <span className="text-xs font-semibold text-neutral-600">Review message</span>
                        <textarea
                          value={selected.data?.message || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { message: e.target.value } })}
                          disabled={readOnly}
                          rows={3}
                          className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        />
                      </label>
                      <label className="mt-4 flex items-center gap-2 text-sm text-neutral-600">
                        <input
                          type="checkbox"
                          checked={!!selected.data?.require_approval}
                          onChange={(e) => onUpdateNode(selected.id, { data: { require_approval: e.target.checked } })}
                          disabled={readOnly}
                        />
                        Require approval (pauses run)
                      </label>
                    </>
                  )}

                  {selected.type === "agent" && (
                    <>
                      <label className="mt-6 block">
                        <span className="text-xs font-semibold text-neutral-600">Tools (comma-separated)</span>
                        <input
                          value={(selected.data?.tools || []).join(", ")}
                          onChange={(e) =>
                            onUpdateNode(selected.id, {
                              data: { tools: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) },
                            })
                          }
                          disabled={readOnly}
                          className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                          placeholder="summarize, calculator, kb_search"
                        />
                      </label>
                      <label className="mt-4 block">
                        <span className="text-xs font-semibold text-neutral-600">System prompt</span>
                        <textarea
                          value={selected.data?.prompt || ""}
                          onChange={(e) => onUpdateNode(selected.id, { data: { prompt: e.target.value } })}
                          disabled={readOnly}
                          rows={3}
                          className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                        />
                      </label>
                      {(selected.data?.tools || []).includes("kb_search") && (
                        <label className="mt-4 block">
                          <span className="text-xs font-semibold text-neutral-600">Knowledge base (kb_search)</span>
                          <select
                            value={selected.data?.knowledge_id ?? ""}
                            onChange={(e) =>
                              onUpdateNode(selected.id, {
                                data: { knowledge_id: e.target.value ? Number(e.target.value) : null },
                              })
                            }
                            disabled={readOnly}
                            className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
                          >
                            <option value="">Select knowledge base</option>
                            {knowledgeBases.map((kb) => (
                              <option key={kb.id} value={kb.id}>
                                {kb.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                    </>
                  )}

                  {!readOnly && onConnect && otherNodes.length > 0 && (
                    <div className="mt-6 rounded-xl border border-black/[0.06] bg-white/50 p-3">
                      <p className="text-xs font-semibold text-neutral-600">Connections</p>
                      <p className="mt-1 text-[11px] text-neutral-400">
                        New nodes stay unconnected — use Connect from / Connect to below.
                      </p>

                      {incoming.length > 0 && (
                        <div className="mt-3">
                          <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-400">
                            Incoming
                          </p>
                          <ul className="mt-1.5 space-y-1.5">
                            {incoming.map((e) => {
                              const source = nodes.find((n) => n.id === e.from);
                              return (
                                <li
                                  key={`in-${e.from}-${e.to}`}
                                  className="flex items-center justify-between gap-2 rounded-lg bg-white/80 px-2.5 py-1.5 text-xs"
                                >
                                  <span className="truncate text-neutral-700">
                                    ← {source ? nodeLabel(source) : e.from}
                                    {source ? ` (${source.type})` : ""}
                                  </span>
                                  {onDisconnect && (
                                    <button
                                      type="button"
                                      onClick={() => onDisconnect(e.from, e.to)}
                                      className="shrink-0 text-[10px] font-semibold text-red-600 hover:text-red-700"
                                    >
                                      Remove
                                    </button>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}

                      {selected.type !== "trigger" && (
                        <div className="mt-3 flex gap-2">
                          <select
                            value={connectSource}
                            onChange={(e) => setConnectSource(e.target.value)}
                            className="min-w-0 flex-1 rounded-lg border border-black/10 bg-white/90 px-2 py-2 text-xs"
                          >
                            <option value="">Connect from…</option>
                            {otherNodes.map((n) => (
                              <option key={n.id} value={n.id}>
                                {nodeLabel(n)} ({n.type})
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            disabled={!connectSource}
                            onClick={() => {
                              if (connectSource) {
                                onConnect(connectSource, selected.id);
                                setConnectSource("");
                              }
                            }}
                            className="shrink-0 rounded-lg bg-neutral-900 px-3 py-2 text-[11px] font-semibold text-white disabled:opacity-40"
                          >
                            Link
                          </button>
                        </div>
                      )}

                      {outgoing.length > 0 && (
                        <div className="mt-4">
                          <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-400">
                            Outgoing
                          </p>
                          <ul className="mt-1.5 space-y-1.5">
                            {outgoing.map((e) => {
                              const target = nodes.find((n) => n.id === e.to);
                              return (
                                <li
                                  key={`out-${e.from}-${e.to}`}
                                  className="flex items-center justify-between gap-2 rounded-lg bg-white/80 px-2.5 py-1.5 text-xs"
                                >
                                  <span className="truncate text-neutral-700">
                                    → {target ? nodeLabel(target) : e.to}
                                    {target ? ` (${target.type})` : ""}
                                  </span>
                                  {onDisconnect && (
                                    <button
                                      type="button"
                                      onClick={() => onDisconnect(e.from, e.to)}
                                      className="shrink-0 text-[10px] font-semibold text-red-600 hover:text-red-700"
                                    >
                                      Remove
                                    </button>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}

                      {selected.type !== "output" && (
                        <div className="mt-3 flex gap-2">
                          <select
                            value={connectTarget}
                            onChange={(e) => setConnectTarget(e.target.value)}
                            className="min-w-0 flex-1 rounded-lg border border-black/10 bg-white/90 px-2 py-2 text-xs"
                          >
                            <option value="">Connect to…</option>
                            {otherNodes.map((n) => (
                              <option key={n.id} value={n.id}>
                                {nodeLabel(n)} ({n.type})
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            disabled={!connectTarget}
                            onClick={() => {
                              if (connectTarget) {
                                onConnect(selected.id, connectTarget);
                                setConnectTarget("");
                              }
                            }}
                            className="shrink-0 rounded-lg bg-neutral-900 px-3 py-2 text-[11px] font-semibold text-white disabled:opacity-40"
                          >
                            Link
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </motion.div>
          )}

          {tab === "test" && (
            <motion.div
              key="test"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.25, ease }}
            >
              <p className="workspace-section-label">Test run</p>
              <p className="mt-1 text-sm text-neutral-500">Execute the full pipeline with sample input.</p>
              <textarea
                value={runInput}
                onChange={(e) => onRunInputChange(e.target.value)}
                rows={5}
                placeholder="Enter a question or topic…"
                className="mt-4 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              />
              <button
                type="button"
                onClick={onRun}
                disabled={running || !runInput.trim() || readOnly}
                className="btn-primary mt-4 w-full"
              >
                {running ? "Running pipeline…" : "Run workflow"}
              </button>

              {runResult && (
                <div className="mt-5 space-y-3">
                  <div className="rounded-xl border border-white/70 bg-white/75 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-400">Output</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-neutral-800">
                      {runResult.output}
                    </p>
                    <p className="mt-3 text-xs text-neutral-400">{runResult.duration_ms}ms</p>
                  </div>
                  {runResult.steps?.length > 0 && (
                    <div className="relative mt-4 pl-4">
                      <div className="absolute bottom-2 left-[5px] top-2 w-px bg-neutral-200" />
                      <ul className="space-y-3">
                        {runResult.steps.map((step, i) => (
                          <motion.li
                            key={step.node_id}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.08 }}
                            className="relative flex items-center gap-3"
                          >
                            <span className="relative z-10 flex h-2.5 w-2.5 shrink-0 rounded-full bg-neutral-900 ring-4 ring-white" />
                            <div className="min-w-0 flex-1 rounded-lg bg-white/70 px-3 py-2">
                              <span className="text-xs font-semibold capitalize text-neutral-800">{step.type}</span>
                              <span className="ml-2 text-[10px] text-emerald-600">{step.status}</span>
                              {step.status === "running" && (
                                <span className="ml-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                              )}
                            </div>
                          </motion.li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}

          {tab === "history" && (
            <motion.div
              key="history"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.25, ease }}
            >
              <p className="workspace-section-label">Recent runs</p>
              {recentRuns.length === 0 ? (
                <p className="mt-4 text-sm text-neutral-500">No runs yet. Use Test run to execute the pipeline.</p>
              ) : (
                <ul className="mt-4 space-y-2">
                  {recentRuns.map((run) => (
                    <li key={run.id} className="workspace-list-row rounded-xl px-4 py-3">
                      <p className="truncate text-sm font-medium">{run.input || "—"}</p>
                      <p className="mt-1 truncate text-xs text-neutral-500">{run.output}</p>
                      <p className="mt-1 text-[10px] text-neutral-400">{run.duration_ms}ms</p>
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </aside>
  );
}
