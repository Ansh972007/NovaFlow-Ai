"use client";

import { useEffect, useState } from "react";
import { listCredentials } from "@/lib/api/credentials";
import {
  createNodeDefinition,
  probeNodeHttp,
  publishNodeDefinition,
  testNodeDefinition,
} from "@/lib/api/nodes";

export default function CreateApiNodeModal({ open, onClose, onSaved }) {
  const [url, setUrl] = useState("{{base_url}}/v1/resource");
  const [method, setMethod] = useState("GET");
  const [body, setBody] = useState("");
  const [auth, setAuth] = useState("custom");
  const [credentialId, setCredentialId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [slug, setSlug] = useState("");
  const [headersJson, setHeadersJson] = useState("{}");
  const [credentials, setCredentials] = useState([]);
  const [probeResult, setProbeResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    listCredentials()
      .then((rows) => setCredentials(Array.isArray(rows) ? rows : []))
      .catch(() => setCredentials([]));
  }, [open]);

  if (!open) return null;

  async function handleProbe() {
    setBusy(true);
    setError("");
    setProbeResult(null);
    try {
      let headers = {};
      try {
        headers = JSON.parse(headersJson || "{}");
      } catch {
        throw new Error("Headers must be valid JSON");
      }
      const result = await probeNodeHttp({
        http: {
          url,
          method,
          body,
          auth,
          credential_id: credentialId || null,
          headers,
        },
        context: { input: "probe", output: "" },
      });
      setProbeResult(result);
      if (!result?.ok) setError(result?.error || "Probe failed");
    } catch (err) {
      setError(err.message || "Probe failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(publish = false) {
    setBusy(true);
    setError("");
    try {
      let headers = {};
      try {
        headers = JSON.parse(headersJson || "{}");
      } catch {
        throw new Error("Headers must be valid JSON");
      }
      const definition = {
        display_name: displayName || "Custom API",
        slug: slug || undefined,
        runtime: "http_declarative",
        http: {
          url,
          method,
          body,
          auth,
          credential_id: credentialId || null,
          headers,
        },
        input_schema: { fields: [] },
        output_mapping: { path: "", template: "{{json}}" },
        ports: { in: 1, out: 1 },
        icon: "api",
        tags: [],
      };
      const created = await createNodeDefinition({
        display_name: definition.display_name,
        slug: slug || undefined,
        definition,
      });
      const testRes = await testNodeDefinition(created.id, { context: { input: "test" } });
      if (!testRes?.ok) {
        setError(testRes?.error || "Test failed after save");
        setProbeResult(testRes);
        return;
      }
      let finalRow = created;
      if (publish) {
        finalRow = await publishNodeDefinition(created.id);
      }
      onSaved?.(finalRow);
      onClose?.();
    } catch (err) {
      setError(err.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const customCreds = credentials.filter((c) => c.category === "custom" || c.kind === "custom");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Create API node</h2>
            <p className="mt-1 text-sm text-neutral-500">Probe your API, then save to your node library.</p>
          </div>
          <button type="button" onClick={onClose} className="text-neutral-400 hover:text-neutral-700">×</button>
        </div>

        <label className="mt-4 block">
          <span className="text-xs font-semibold text-neutral-600">Display name</span>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="mt-1 w-full rounded-xl border border-black/10 px-3 py-2 text-sm"
            placeholder="Stripe — List charges"
          />
        </label>
        <label className="mt-3 block">
          <span className="text-xs font-semibold text-neutral-600">Slug (optional)</span>
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            className="mt-1 w-full rounded-xl border border-black/10 px-3 py-2 text-sm"
            placeholder="stripe_list_charges"
          />
        </label>
        <label className="mt-3 block">
          <span className="text-xs font-semibold text-neutral-600">URL</span>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="mt-1 w-full rounded-xl border border-black/10 px-3 py-2 text-sm"
          />
        </label>
        <label className="mt-3 block">
          <span className="text-xs font-semibold text-neutral-600">Method</span>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="mt-1 w-full rounded-xl border border-black/10 px-3 py-2 text-sm"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
          </select>
        </label>
        <label className="mt-3 block">
          <span className="text-xs font-semibold text-neutral-600">Body template</span>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            className="mt-1 w-full resize-none rounded-xl border border-black/10 px-3 py-2 text-sm"
          />
        </label>
        <label className="mt-3 block">
          <span className="text-xs font-semibold text-neutral-600">Headers (JSON)</span>
          <textarea
            value={headersJson}
            onChange={(e) => setHeadersJson(e.target.value)}
            rows={2}
            className="mt-1 w-full resize-none rounded-xl border border-black/10 px-3 py-2 text-sm font-mono"
          />
        </label>
        <label className="mt-3 block">
          <span className="text-xs font-semibold text-neutral-600">Credential</span>
          <select
            value={credentialId}
            onChange={(e) => setCredentialId(e.target.value)}
            className="mt-1 w-full rounded-xl border border-black/10 px-3 py-2 text-sm"
          >
            <option value="">Default custom API credential</option>
            {customCreds.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label} ({c.kind}){c.is_default ? " · default" : ""}
              </option>
            ))}
          </select>
        </label>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {probeResult && (
          <div className="mt-3 rounded-xl bg-neutral-50 p-3 text-xs text-neutral-700">
            <p className="font-semibold">
              Probe: {probeResult.ok ? "OK" : "Failed"} · HTTP {probeResult.status_code || "—"}
            </p>
            <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap">{probeResult.body_preview || ""}</pre>
          </div>
        )}

        <div className="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={handleProbe}
            className="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Working…" : "Probe"}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => handleSave(false)}
            className="rounded-xl border border-black/10 px-4 py-2 text-sm font-semibold"
          >
            Save draft
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => handleSave(true)}
            className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Save & publish
          </button>
        </div>
      </div>
    </div>
  );
}
