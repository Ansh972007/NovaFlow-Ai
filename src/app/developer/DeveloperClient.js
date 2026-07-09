"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import { getApiBaseUrl } from "@/lib/api/config";

const ease = [0.16, 1, 0.3, 1];
const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

const spring = { type: "spring", stiffness: 420, damping: 34 };

const PRESET_GROUPS = [
  {
    id: "core",
    label: "Core",
    tagline: "Workflows, knowledge, keys",
    borderAnim: "march",
    innerAnim: "grid",
    presets: [
      { label: "Health", method: "GET", path: "/api/health" },
      { label: "List workflows", method: "GET", path: "/workflow?page=1&limit=10" },
      { label: "Templates", method: "GET", path: "/workflow/templates" },
      { label: "Knowledge", method: "GET", path: "/knowledge?page_num=1&page_size=10" },
      { label: "API keys", method: "GET", path: "/api-keys" },
      { label: "Schedules", method: "GET", path: "/workflow/schedules" },
      { label: "Runs", method: "GET", path: "/workflow/runs?limit=20" },
      { label: "Projects", method: "GET", path: "/projects" },
    ],
  },
  {
    id: "integrations",
    label: "Integrations",
    tagline: "Slack, Discord, webhooks",
    borderAnim: "shimmer",
    innerAnim: "nodes",
    presets: [
      { label: "Settings", method: "GET", path: "/integrations/settings" },
      { label: "Health", method: "GET", path: "/integrations/health" },
      { label: "Telegram status", method: "GET", path: "/integrations/telegram/webhook-status" },
      { label: "Test Slack", method: "POST", path: "/integrations/slack/test", body: '{\n  "message": "Hello from NovaFlow Slack test"\n}' },
      { label: "Test Discord", method: "POST", path: "/integrations/discord/test", body: '{\n  "message": "Hello from Discord test"\n}' },
      { label: "Verify Linear", method: "POST", path: "/integrations/linear/verify", body: "{}" },
      { label: "Verify GitHub", method: "POST", path: "/integrations/github/verify", body: "{}" },
      { label: "Test Telegram", method: "POST", path: "/integrations/notify/test", body: '{\n  "channel": "telegram",\n  "to": "YOUR_CHAT_ID",\n  "message": "Hello from API"\n}' },
    ],
  },
  {
    id: "agents",
    label: "Agents & Eval",
    tagline: "Tools, runs, suites",
    borderAnim: "pulse",
    innerAnim: "wave",
    presets: [
      { label: "Saved agents", method: "GET", path: "/agents" },
      { label: "Agent tools", method: "GET", path: "/agents/tools" },
      { label: "Run agent", method: "POST", path: "/agents/run", body: '{\n  "input": "Summarize: NovaFlow ships Discord, Linear, Runs, and Slack Events.",\n  "tools": ["summarize", "word_count"]\n}' },
      { label: "Eval suites", method: "GET", path: "/eval/suites" },
    ],
  },
  {
    id: "lab",
    label: "Model Lab",
    tagline: "Train, drift, pipelines",
    borderAnim: "trace",
    innerAnim: "spark",
    presets: [
      { label: "Pipelines", method: "GET", path: "/model-lab/pipelines" },
      { label: "Prompt drift", method: "GET", path: "/model-lab/drift" },
      { label: "Train + eval", method: "POST", path: "/model-lab/train-and-eval", body: '{\n  "dataset_id": 1,\n  "base_model": "gpt-4o-mini-2024-07-18",\n  "auto_eval_suite_id": 1\n}' },
    ],
  },
];

function buildUrl(path) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return cleanPath.startsWith("/api/") ? cleanPath : `/api/v1${cleanPath}`;
}

function buildFullUrl(path) {
  const base = getApiBaseUrl().replace(/\/$/, "");
  return `${base}${buildUrl(path)}`;
}

function buildCurl({ method, path, body, apiKey }) {
  const url = buildFullUrl(path);
  const lines = [`curl -X ${method} '${url}'`, `  -H 'Content-Type: application/json'`];
  if (apiKey?.trim()) {
    lines.push(`  -H 'X-Api-Key: ${apiKey.trim()}'`);
  } else {
    lines.push(`  -H 'Authorization: Bearer <session_token>'`);
    lines.push(`  -H 'X-Workspace-Id: <workspace_id>'`);
  }
  if (method !== "GET" && method !== "HEAD" && body?.trim()) {
    lines.push(`  -d '${body.replace(/'/g, "'\\''")}'`);
  }
  return lines.join(" \\\n");
}

function MethodBadge({ method, small = false }) {
  const isGet = method === "GET" || method === "HEAD";
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-md border font-bold tracking-wide uppercase ${
        small ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-0.5 text-[10px]"
      } ${isGet ? "border-black bg-white text-black" : "border-black bg-black text-white"}`}
    >
      {method}
    </span>
  );
}

function StatusBadge({ ok, status }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold tracking-wide uppercase ${
        ok ? "border-black bg-black text-white" : "border-black bg-white text-black"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-white" : "bg-black"}`} />
      HTTP {status}
    </span>
  );
}

function PresetBorder({ type, active }) {
  if (!active) return null;
  const r = 12;
  const common = "pointer-events-none absolute inset-0 h-full w-full overflow-visible";

  if (type === "march") {
    return (
      <svg className={common} preserveAspectRatio="none" viewBox="0 0 100 100">
        <motion.rect
          x="1" y="1" width="98" height="98" rx={r}
          fill="none" stroke="black" strokeWidth="2"
          strokeDasharray="8 5"
          animate={{ strokeDashoffset: [0, -26] }}
          transition={{ duration: 1.1, repeat: Infinity, ease: "linear" }}
        />
      </svg>
    );
  }
  if (type === "shimmer") {
    return (
      <svg className={common} preserveAspectRatio="none" viewBox="0 0 100 100">
        <motion.rect
          x="1" y="1" width="98" height="98" rx={r}
          fill="none" stroke="black" strokeWidth="2"
          strokeDasharray="3 12 20 8"
          animate={{ strokeDashoffset: [0, -86] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "linear" }}
        />
      </svg>
    );
  }
  if (type === "pulse") {
    return (
      <>
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-xl border border-black"
          animate={{ opacity: [0.5, 0], scale: [1, 1.03] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
        />
        <svg className={common} preserveAspectRatio="none" viewBox="0 0 100 100">
          <motion.rect
            x="1" y="1" width="98" height="98" rx={r}
            fill="none" stroke="black" strokeWidth="2"
            animate={{ strokeOpacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
          />
        </svg>
      </>
    );
  }
  if (type === "trace") {
    return (
      <svg className={common} preserveAspectRatio="none" viewBox="0 0 100 100">
        <motion.rect
          x="1" y="1" width="98" height="98" rx={r}
          fill="none" stroke="black" strokeWidth="2.5"
          pathLength="1" strokeDasharray="0.12 0.88"
          animate={{ strokeDashoffset: [0, -1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        />
      </svg>
    );
  }
  return null;
}

function PresetInnerDecor({ type, active }) {
  if (!active) return null;

  if (type === "grid") {
    return (
      <div className="flex h-4 gap-0.5">
        {[0, 1, 2, 3].map((i) => (
          <motion.span
            key={i}
            className="w-1 rounded-sm bg-black"
            animate={{ scaleY: [0.3, 1, 0.3], opacity: [0.2, 0.8, 0.2] }}
            transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.1 }}
          />
        ))}
      </div>
    );
  }
  if (type === "nodes") {
    return (
      <svg className="h-4 w-12" viewBox="0 0 48 16">
        <motion.circle cx="8" cy="8" r="2" fill="black" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity }} />
        <motion.circle cx="24" cy="8" r="2" fill="black" animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }} />
        <motion.circle cx="40" cy="8" r="2" fill="black" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }} />
        <motion.line x1="10" y1="8" x2="22" y2="8" stroke="black" strokeWidth="1" animate={{ pathLength: [0, 1, 0] }} transition={{ duration: 1.5, repeat: Infinity }} />
        <motion.line x1="26" y1="8" x2="38" y2="8" stroke="black" strokeWidth="1" animate={{ pathLength: [0, 1, 0] }} transition={{ duration: 1.5, repeat: Infinity, delay: 0.3 }} />
      </svg>
    );
  }
  if (type === "wave") {
    return (
      <div className="flex h-4 items-end gap-px">
        {[0.4, 0.8, 1, 0.6].map((h, i) => (
          <motion.span
            key={i}
            className="w-1 rounded-full bg-black"
            style={{ height: `${h * 14}px` }}
            animate={{ scaleY: [0.25, 1, 0.35] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.08 }}
          />
        ))}
      </div>
    );
  }
  if (type === "spark") {
    return (
      <motion.svg className="h-4 w-10" viewBox="0 0 40 16">
        <motion.path
          d="M4 12 L12 4 L20 10 L28 2 L36 8"
          fill="none" stroke="black" strokeWidth="1.5"
          pathLength="1" strokeDasharray="0.2 0.8"
          animate={{ strokeDashoffset: [0, -1] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
        />
      </motion.svg>
    );
  }
  return null;
}

function PresetCategoryTabs({ groups, active, onChange }) {
  return (
    <div className="relative flex flex-wrap gap-2">
      {groups.map((g) => (
        <button
          key={g.id}
          type="button"
          onClick={() => onChange(g.id)}
          className={`relative overflow-hidden rounded-full px-5 py-2.5 text-sm font-semibold transition-colors ${
            active === g.id ? "text-white" : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
          }`}
        >
          {active === g.id && (
            <motion.span
              layoutId="preset-tab-pill"
              className="absolute inset-0 rounded-full bg-black"
              transition={spring}
            />
          )}
          <span className="relative z-10">{g.label}</span>
        </button>
      ))}
    </div>
  );
}

function PresetCard({ preset, active, onSelect, index, borderAnim, innerAnim, reducedMotion }) {
  const isPost = preset.method !== "GET" && preset.method !== "HEAD";

  return (
    <motion.button
      type="button"
      layout
      initial={{ opacity: 0, y: 20, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 12, scale: 0.96 }}
      transition={{ delay: reducedMotion ? 0 : index * 0.04, duration: 0.4, ease }}
      whileHover={reducedMotion ? {} : { y: -4, transition: { duration: 0.2 } }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(preset)}
      className={`noise group relative flex h-full min-h-[7.5rem] w-full flex-col overflow-hidden rounded-[1.15rem] border text-left transition-shadow duration-300 ${
        active
          ? "border-transparent bg-neutral-50 shadow-[0_16px_48px_-16px_rgba(0,0,0,0.35)]"
          : "border-neutral-200 bg-white hover:border-neutral-400 hover:shadow-lg hover:shadow-black/8"
      }`}
    >
      {!reducedMotion && <PresetBorder type={borderAnim} active={active} />}

      {active && (
        <motion.span
          className="pointer-events-none absolute inset-0 bg-black/[0.03]"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.08, 0, 0.08] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}

      <div className="relative flex flex-1 flex-col p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <motion.div
            animate={active && isPost ? { scale: [1, 1.08, 1] } : {}}
            transition={{ duration: 0.8, repeat: active ? Infinity : 0, repeatDelay: 1 }}
          >
            <MethodBadge method={preset.method} />
          </motion.div>
          {!reducedMotion && <PresetInnerDecor type={innerAnim} active={active} />}
        </div>

        <h3 className="mt-4 font-serif text-lg tracking-tight text-neutral-900">{preset.label}</h3>

        <motion.p
          className="mt-2 line-clamp-2 flex-1 font-mono text-[11px] leading-relaxed text-neutral-500"
          animate={active ? { opacity: [0.55, 1, 0.55] } : {}}
          transition={{ duration: 2, repeat: active ? Infinity : 0 }}
        >
          {preset.path}
        </motion.p>

        <div className="mt-4 flex items-center justify-between">
          <span
            className={`text-xs font-semibold tracking-wide uppercase ${
              active ? "text-black" : "text-neutral-400 opacity-0 transition-opacity group-hover:opacity-100"
            }`}
          >
            {active ? "Loaded" : "Use preset →"}
          </span>
          <motion.span
            className={`text-lg text-neutral-400 ${active ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}
            animate={active ? { x: [0, 4, 0] } : {}}
            transition={{ duration: 1.2, repeat: active ? Infinity : 0 }}
          >
            →
          </motion.span>
        </div>
      </div>

      {active && !reducedMotion && (
        <motion.div
          className="absolute bottom-0 left-0 h-1 bg-black"
          initial={{ width: "0%" }}
          animate={{ width: "100%" }}
          transition={{ duration: 0.5, ease }}
        />
      )}
    </motion.button>
  );
}

function PresetsSection({ groups, presetGroup, setPresetGroup, currentPresets, activePreset, applyPreset, history, replayHistory }) {
  const reducedMotion = useReducedMotion();
  const activeGroup = groups.find((g) => g.id === presetGroup);

  return (
    <section className="mt-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, ease }}
        className="mb-6 flex flex-wrap items-end justify-between gap-4"
      >
        <div>
          <p className="workspace-section-label">Quick start</p>
          <h2 className="mt-1 font-serif text-3xl tracking-tight text-neutral-900 sm:text-4xl">API Presets</h2>
          <AnimatePresence mode="wait">
            <motion.p
              key={presetGroup}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.25 }}
              className="mt-2 max-w-xl text-sm leading-relaxed text-neutral-500"
            >
              {activeGroup?.tagline} — click a card to load method, path, and body into the request builder below.
            </motion.p>
          </AnimatePresence>
        </div>
        <motion.span
          key={currentPresets.length}
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-bold text-neutral-700 shadow-sm"
        >
          {currentPresets.length} endpoints
        </motion.span>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12, ease }}
        className="workspace-panel noise relative overflow-hidden rounded-[1.75rem] p-6 sm:p-8"
      >
        {!reducedMotion && (
          <motion.div
            className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-black/20 to-transparent"
            animate={{ y: [0, 420, 0], opacity: [0, 0.5, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
          />
        )}

        <PresetCategoryTabs groups={groups} active={presetGroup} onChange={setPresetGroup} />

        <div className="relative mt-6">
          <AnimatePresence mode="popLayout">
            <motion.div
              key={presetGroup}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            >
              {currentPresets.map((p, i) => (
                <PresetCard
                  key={`${presetGroup}-${p.label}`}
                  preset={p}
                  index={i}
                  active={activePreset === p.label}
                  onSelect={applyPreset}
                  borderAnim={activeGroup?.borderAnim}
                  innerAnim={activeGroup?.innerAnim}
                  reducedMotion={reducedMotion}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        </div>

        {history.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-8 border-t border-black/[0.06] pt-6"
          >
            <p className="text-[11px] font-semibold tracking-[0.16em] text-neutral-400 uppercase">Recent requests</p>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {history.map((h, i) => (
                <motion.button
                  key={h.at}
                  type="button"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  onClick={() => replayHistory(h)}
                  className="flex shrink-0 items-center gap-2 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-left transition hover:border-neutral-400 hover:shadow-md"
                >
                  <MethodBadge method={h.method} small />
                  <span className="max-w-[12rem] truncate font-mono text-[11px] text-neutral-600">{h.path}</span>
                  <span className="text-[10px] font-medium text-neutral-400">{h.ms}ms</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>
    </section>
  );
}

function ResponseTerminal({ response, onCopy, onDownload, onCopyCurl, curl }) {
  const json = JSON.stringify(response.data, null, 2);
  const size = new Blob([json]).size;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.45, ease }}
      className="relative"
    >
      <div className="absolute -inset-3 rounded-[2rem] bg-gradient-to-b from-neutral-200/30 to-transparent blur-2xl" />
      <div className="relative overflow-hidden rounded-[1.35rem] border border-neutral-200 bg-white shadow-2xl shadow-black/10">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-100 bg-neutral-50 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-neutral-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-neutral-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-neutral-300" />
            </div>
            <span className="ml-1 text-[11px] font-medium text-neutral-500">Response</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge ok={response.ok} status={response.status} />
            <span className="rounded-full border border-neutral-200 bg-white px-2 py-0.5 text-[10px] font-medium text-neutral-600">
              {response.ms} ms
            </span>
            <span className="rounded-full border border-neutral-200 bg-white px-2 py-0.5 text-[10px] font-medium text-neutral-500">
              {(size / 1024).toFixed(1)} KB
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 border-b border-neutral-100 px-4 py-2">
          <button type="button" onClick={onCopy} className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]">
            Copy JSON
          </button>
          <button type="button" onClick={onDownload} className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]">
            Download
          </button>
          <button type="button" onClick={onCopyCurl} className="workspace-btn-ghost !px-2.5 !py-1 text-[11px]">
            Copy cURL
          </button>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="max-h-[28rem] overflow-auto bg-neutral-950 p-4"
        >
          <pre className="font-mono text-[12px] leading-relaxed text-neutral-100">{json}</pre>
        </motion.div>
      </div>
      {curl && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mt-3 overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 p-3"
        >
          <p className="text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">cURL</p>
          <pre className="mt-2 overflow-x-auto font-mono text-[10px] leading-relaxed text-neutral-700">{curl}</pre>
        </motion.div>
      )}
    </motion.div>
  );
}

export default function DeveloperClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [method, setMethod] = useState("GET");
  const [path, setPath] = useState("/workflow?page=1&limit=5");
  const [body, setBody] = useState('{\n  "workflow_id": "",\n  "input": "Hello"\n}');
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [presetGroup, setPresetGroup] = useState("core");
  const [activePreset, setActivePreset] = useState("");
  const [history, setHistory] = useState([]);
  const [showCurl, setShowCurl] = useState(false);

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
    checkBackendHealth().then(setHealth).catch(() => setHealth({ ok: false }));
  }, [router]);

  const fullUrl = useMemo(() => buildFullUrl(path), [path]);
  const curl = useMemo(() => buildCurl({ method, path, body, apiKey }), [method, path, body, apiKey]);

  const currentPresets = useMemo(
    () => PRESET_GROUPS.find((g) => g.id === presetGroup)?.presets || [],
    [presetGroup]
  );

  const applyPreset = useCallback((preset) => {
    setMethod(preset.method);
    setPath(preset.path);
    setActivePreset(preset.label);
    if (preset.body) setBody(preset.body);
    else if (preset.method === "GET" || preset.method === "HEAD") setBody("");
    setError("");
    setMsg("");
  }, []);

  const replayHistory = useCallback((item) => {
    setMethod(item.method);
    setPath(item.path);
    if (item.body) setBody(item.body);
    setActivePreset("");
  }, []);

  async function sendRequest(e) {
    e?.preventDefault();
    setBusy(true);
    setError("");
    setMsg("");
    setResponse(null);

    const url = buildUrl(path);
    const headers = { "Content-Type": "application/json" };
    if (apiKey.trim()) {
      headers["X-Api-Key"] = apiKey.trim();
    } else if (typeof window !== "undefined") {
      const token = localStorage.getItem("nf_token");
      if (token) headers.Authorization = `Bearer ${token}`;
      const wid = localStorage.getItem("nf_workspace_id");
      if (wid) headers["X-Workspace-Id"] = wid;
    }
    const opts = { method, headers, cache: "no-store" };
    if (method !== "GET" && method !== "HEAD" && body.trim()) {
      opts.body = body;
    }
    const started = performance.now();
    try {
      const res = await fetch(url, opts);
      const text = await res.text();
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = text;
      }
      const ms = Math.round(performance.now() - started);
      const result = { status: res.status, ok: res.ok, ms, data: parsed };
      setResponse(result);
      setHistory((prev) => [
        { method, path, body: method !== "GET" ? body : "", status: res.status, ms, at: Date.now() },
        ...prev.slice(0, 7),
      ]);
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setBusy(false);
    }
  }

  function copyJson() {
    if (!response) return;
    navigator.clipboard.writeText(JSON.stringify(response.data, null, 2));
    setMsg("Response copied to clipboard.");
  }

  function downloadJson() {
    if (!response) return;
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `api-response-${response.status}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function copyCurl() {
    navigator.clipboard.writeText(curl);
    setMsg("cURL command copied.");
    setShowCurl(true);
  }

  return (
    <WorkspacePageShell user={user} loading={!user} loadingMessage="Loading playground…" maxWidth="max-w-7xl">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
        <WorkspaceHero
          eyebrow="Developer tools"
          title="API"
          titleHighlight="playground"
          description="Send test requests to the NovaFlow REST API. Session auth is used by default — paste an API key to override."
          badge={
            <span
              className={`workspace-badge-live inline-flex items-center gap-2 ${
                !health?.ok ? "!border-neutral-400 !bg-neutral-100 !text-neutral-700" : ""
              }`}
            >
              <span className="relative flex h-2 w-2">
                {health?.ok && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-neutral-400 opacity-60" />
                )}
                <span className={`relative inline-flex h-2 w-2 rounded-full ${health?.ok ? "bg-neutral-900" : "bg-neutral-400"}`} />
              </span>
              {health?.ok ? "API online" : "API offline"}
            </span>
          }
          actions={
            <Link href="/settings" className="workspace-btn-ghost shrink-0 text-sm">
              Manage API keys →
            </Link>
          }
        />

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5, ease }}
          className="mt-8 grid gap-4 sm:grid-cols-3"
        >
          <WorkspaceStatCard
            label="Base URL"
            value={health?.ok ? "Ready" : "Offline"}
            hint={`${getApiBaseUrl()}/api/v1`}
          />
          <WorkspaceStatCard label="Method" value={method} hint="Current request" />
          <WorkspaceStatCard
            label="Last response"
            value={response ? `HTTP ${response.status}` : "—"}
            hint={response ? `${response.ms} ms` : "Send a request"}
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

        <PresetsSection
          groups={PRESET_GROUPS}
          presetGroup={presetGroup}
          setPresetGroup={setPresetGroup}
          currentPresets={currentPresets}
          activePreset={activePreset}
          applyPreset={applyPreset}
          history={history}
          replayHistory={replayHistory}
        />

        <div className="mt-10 space-y-6">
            <motion.form
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, ease }}
              onSubmit={sendRequest}
              className="workspace-panel noise overflow-hidden rounded-[1.5rem]"
            >
              <div className="border-b border-black/[0.06] bg-gradient-to-r from-neutral-50 to-white px-5 py-4 sm:px-6">
                <p className="text-[11px] font-semibold tracking-[0.16em] text-neutral-400 uppercase">Request builder</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {METHODS.map((m) => (
                    <motion.button
                      key={m}
                      type="button"
                      whileTap={{ scale: 0.96 }}
                      onClick={() => setMethod(m)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-bold tracking-wide uppercase transition ${
                        method === m ? "bg-black text-white shadow-md" : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                      }`}
                    >
                      {m}
                    </motion.button>
                  ))}
                </div>
              </div>

              <div className="space-y-4 p-5 sm:p-6">
                <div className="rounded-xl border border-black/[0.06] bg-neutral-950 px-4 py-3">
                  <p className="text-[10px] font-semibold tracking-widest text-neutral-500 uppercase">Full URL</p>
                  <p className="mt-1 break-all font-mono text-[11px] leading-relaxed text-neutral-200">{fullUrl}</p>
                </div>

                <label className="block">
                  <span className="text-xs font-semibold text-neutral-700">API key (optional)</span>
                  <input
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="nf_… overrides session auth"
                    className="input-field mt-2 w-full font-mono text-xs"
                  />
                </label>

                <label className="block">
                  <span className="text-xs font-semibold text-neutral-700">Path</span>
                  <input
                    value={path}
                    onChange={(e) => {
                      setPath(e.target.value);
                      setActivePreset("");
                    }}
                    placeholder="/workflow"
                    className="input-field mt-2 w-full font-mono text-xs"
                  />
                </label>

                <AnimatePresence>
                  {method !== "GET" && method !== "HEAD" && (
                    <motion.label
                      key="body"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="block overflow-hidden"
                    >
                      <span className="text-xs font-semibold text-neutral-700">JSON body</span>
                      <textarea
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                        rows={8}
                        className="input-field mt-2 w-full resize-y font-mono text-xs leading-relaxed"
                        spellCheck={false}
                      />
                    </motion.label>
                  )}
                </AnimatePresence>

                <div className="flex flex-wrap gap-3">
                  <motion.button
                    type="submit"
                    disabled={busy}
                    whileHover={busy ? {} : { scale: 1.02 }}
                    whileTap={busy ? {} : { scale: 0.98 }}
                    className="btn-primary disabled:opacity-50"
                  >
                    {busy ? (
                      <span className="inline-flex items-center gap-2">
                        <motion.span
                          className="h-3.5 w-3.5 rounded-full border-2 border-white/30 border-t-white"
                          animate={{ rotate: 360 }}
                          transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
                        />
                        Sending…
                      </span>
                    ) : (
                      "Send request"
                    )}
                  </motion.button>
                  <button type="button" onClick={copyCurl} className="workspace-btn-ghost text-sm">
                    Copy cURL
                  </button>
                </div>
              </div>
            </motion.form>

            <AnimatePresence mode="wait">
              {busy && (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="workspace-panel rounded-[1.5rem] p-6"
                >
                  <div className="space-y-3">
                    {[0, 1, 2, 3].map((i) => (
                      <motion.div
                        key={i}
                        className="h-3 rounded-full bg-neutral-100"
                        style={{ width: `${90 - i * 15}%` }}
                        animate={{ opacity: [0.4, 0.9, 0.4] }}
                        transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.12 }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}

              {response && !busy && (
                <ResponseTerminal
                  key="response"
                  response={response}
                  curl={showCurl ? curl : null}
                  onCopy={copyJson}
                  onDownload={downloadJson}
                  onCopyCurl={copyCurl}
                />
              )}

              {!busy && !response && (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="workspace-empty rounded-[1.5rem] py-16 text-center"
                >
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border-2 border-dashed border-neutral-300">
                    <svg className="h-6 w-6 text-neutral-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M4 7h16M4 12h10M4 17h6" />
                      <path d="M18 12.5 21 16l-3 3.5" />
                    </svg>
                  </div>
                  <p className="mt-4 font-semibold text-neutral-900">No response yet</p>
                  <p className="mt-2 text-sm text-neutral-500">Pick a preset or build a request, then hit Send.</p>
                </motion.div>
              )}
            </AnimatePresence>
        </div>
      </motion.div>
    </WorkspacePageShell>
  );
}
