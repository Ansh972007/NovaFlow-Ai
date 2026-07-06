"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import { getUserInfo } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import { getApiBaseUrl } from "@/lib/api/config";

const ease = [0.16, 1, 0.3, 1];

const PRESETS = [
  { label: "Health", method: "GET", path: "/api/health" },
  { label: "List workflows", method: "GET", path: "/workflow?page=1&limit=10" },
  { label: "List knowledge", method: "GET", path: "/knowledge?page_num=1&page_size=10" },
  { label: "List API keys", method: "GET", path: "/api-keys" },
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
    if (preset.method === "GET") setBody("");
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
        <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-12">
          <Link
            href="/settings"
            className="group mb-8 inline-flex items-center gap-2 text-sm font-medium text-neutral-500 transition-colors hover:text-neutral-900"
          >
            <span className="transition-transform group-hover:-translate-x-1">←</span>
            Settings
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ease }}
            className="workspace-hero rounded-[1.75rem] p-7 sm:p-9"
          >
            <p className="workspace-section-label">Developer</p>
            <h1 className="mt-1 font-serif text-3xl tracking-tight sm:text-4xl">API playground</h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-neutral-500">
              Send test requests to <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">{getApiBaseUrl()}/api/v1</code>.
              Uses your session by default, or paste an API key to test programmatic access.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-semibold">
              <span
                className={`rounded-full px-3 py-1 ring-1 ${
                  health?.ok ? "bg-emerald-50 text-emerald-700 ring-emerald-200" : "bg-red-50 text-red-700 ring-red-200"
                }`}
              >
                API {health?.ok ? "online" : "offline"}
              </span>
            </div>
          </motion.div>

          <motion.form
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.06, ease }}
            onSubmit={sendRequest}
            className="workspace-panel mt-8 space-y-5 rounded-[1.75rem] p-6 sm:p-7"
          >
            <div className="flex flex-wrap gap-2">
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

            {error && <p className="text-sm text-red-600">{error}</p>}

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
              <pre className="mt-4 max-h-[420px] overflow-auto rounded-xl bg-neutral-950 p-4 text-xs leading-relaxed text-emerald-100">
                {JSON.stringify(response.data, null, 2)}
              </pre>
            </motion.div>
          )}
        </main>
      </div>
    </div>
  );
}
