"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceBackLink from "@/components/workspace/WorkspaceBackLink";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import { getApiBaseUrl } from "@/lib/api/config";

const ease = [0.16, 1, 0.3, 1];

const PRESETS = [
  { label: "Health", method: "GET", path: "/api/health" },
  { label: "List workflows", method: "GET", path: "/workflow?page=1&limit=10" },
  { label: "Workflow templates", method: "GET", path: "/workflow/templates" },
  { label: "List knowledge", method: "GET", path: "/knowledge?page_num=1&page_size=10" },
  { label: "List API keys", method: "GET", path: "/api-keys" },
  { label: "Integration settings", method: "GET", path: "/integrations/settings" },
  { label: "Integration health", method: "GET", path: "/integrations/health" },
  { label: "Telegram webhook status", method: "GET", path: "/integrations/telegram/webhook-status" },
  { label: "Test Slack notify", method: "POST", path: "/integrations/slack/test", body: '{\n  "message": "Hello from NovaFlow Slack test"\n}' },
  { label: "Test Discord notify", method: "POST", path: "/integrations/discord/test", body: '{\n  "message": "Hello from Discord test"\n}' },
  { label: "Verify Linear", method: "POST", path: "/integrations/linear/verify", body: "{}" },
  { label: "Verify GitHub", method: "POST", path: "/integrations/github/verify", body: "{}" },
  { label: "List schedules", method: "GET", path: "/workflow/schedules" },
  { label: "List runs", method: "GET", path: "/workflow/runs?limit=20" },
  { label: "List saved agents", method: "GET", path: "/agents" },
  { label: "Agent tools", method: "GET", path: "/agents/tools" },
  { label: "Run agent", method: "POST", path: "/agents/run", body: '{\n  "input": "Summarize: NovaFlow ships Discord, Linear, Runs, and Slack Events.",\n  "tools": ["summarize", "word_count"]\n}' },
  { label: "Eval suites", method: "GET", path: "/eval/suites" },
  { label: "List projects", method: "GET", path: "/projects" },
  { label: "Model Lab pipelines", method: "GET", path: "/model-lab/pipelines" },
  { label: "Prompt drift", method: "GET", path: "/model-lab/drift" },
  { label: "Test Telegram notify", method: "POST", path: "/integrations/notify/test", body: '{\n  "channel": "telegram",\n  "to": "YOUR_CHAT_ID",\n  "message": "Hello from API"\n}' },
  { label: "Train + eval", method: "POST", path: "/model-lab/train-and-eval", body: '{\n  "dataset_id": 1,\n  "base_model": "gpt-4o-mini-2024-07-18",\n  "auto_eval_suite_id": 1\n}' },
];

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

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
    checkBackendHealth().then(setHealth).catch(() => setHealth({ ok: false }));
  }, [router]);

  async function sendRequest(e) {
    e?.preventDefault();
    setBusy(true);
    setError("");
    setResponse(null);
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const url = cleanPath.startsWith("/api/") ? cleanPath : `/api/v1${cleanPath}`;
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
      setResponse({
        status: res.status,
        ok: res.ok,
        ms: Math.round(performance.now() - started),
        data: parsed,
      });
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setBusy(false);
    }
  }

  function applyPreset(preset) {
    setMethod(preset.method);
    setPath(preset.path);
    if (preset.body) setBody(preset.body);
    else if (preset.method === "GET") setBody("");
  }

  return (
    <WorkspacePageShell user={user} maxWidth="max-w-5xl">
      <WorkspaceBackLink href="/settings">Back to settings</WorkspaceBackLink>

      <WorkspaceHero
        eyebrow="Developer"
        title="API"
        titleHighlight="playground"
        description={
          <>
            Send test requests to{" "}
            <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">{getApiBaseUrl()}/api/v1</code>.
            Uses your session by default, or paste an API key.
          </>
        }
        badge={
          health?.ok ? (
            <span className="workspace-badge-live">API online</span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-red-200/80 bg-red-50/90 px-2.5 py-0.5 text-[10px] font-bold uppercase text-red-700">
              Offline
            </span>
          )
        }
        actions={
          <Link href="/settings" className="workspace-btn-ghost shrink-0">
            Manage API keys
          </Link>
        }
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <WorkspaceStatCard
            label="Base URL"
            value={health?.ok ? "Ready" : "Check API"}
            hint={`${getApiBaseUrl()}/api/v1`}
            status={health?.ok ? "online" : "offline"}
          />
          <WorkspaceStatCard label="Method" value={method} hint="Current request type" />
          <WorkspaceStatCard
            label="Last response"
            value={response ? `HTTP ${response.status}` : "—"}
            hint={response ? `${response.ms} ms` : "Send a request"}
          />
        </div>
      </WorkspaceHero>

      <motion.form
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.06, ease }}
        onSubmit={sendRequest}
        className="workspace-panel mt-8 space-y-5 rounded-[1.75rem] p-6 sm:p-7"
      >
        <div>
          <p className="workspace-section-label">Quick presets</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => applyPreset(p)}
                className="workspace-btn-ghost !py-1.5 text-xs"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <label className="block text-sm font-medium">
          API key (optional)
          <input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="nf_… overrides session auth"
            className="input-field mt-1.5 w-full font-mono text-xs"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-[120px_1fr]">
          <label className="block text-sm font-medium">
            Method
            <select value={method} onChange={(e) => setMethod(e.target.value)} className="input-field mt-1.5 w-full">
              {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            Path
            <input
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/workflow"
              className="input-field mt-1.5 w-full font-mono text-xs"
            />
          </label>
        </div>

        {method !== "GET" && method !== "HEAD" && (
          <label className="block text-sm font-medium">
            JSON body
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={6}
              className="input-field mt-1.5 w-full font-mono text-xs"
            />
          </label>
        )}

        {error && <WorkspaceAlert type="error">{error}</WorkspaceAlert>}

        <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
          {busy ? "Sending…" : "Send request"}
        </button>
      </motion.form>

      {response && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="workspace-panel mt-6 rounded-[1.75rem] p-6 sm:p-7"
        >
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                response.ok ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
              }`}
            >
              HTTP {response.status}
            </span>
            <span className="text-xs text-neutral-500">{response.ms} ms</span>
          </div>
          <div className="workspace-output-panel mt-4">
            <pre>{JSON.stringify(response.data, null, 2)}</pre>
          </div>
        </motion.div>
      )}
    </WorkspacePageShell>
  );
}
