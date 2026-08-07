"use client";

import { useState } from "react";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { createKnowledgeSyncJob, runKnowledgeSyncJob } from "@/lib/api/kos";

const CONNECTORS = [
  { id: "manual", label: "Manual (re-index uploads)" },
  { id: "s3", label: "S3 bucket" },
  { id: "git", label: "Git repository" },
  { id: "webhook", label: "Webhook incremental" },
];

export default function KnowledgeSyncPanel({ collectionId, writeable }) {
  const [connector, setConnector] = useState("manual");
  const [configJson, setConfigJson] = useState("{}");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [lastJob, setLastJob] = useState(null);

  async function handleCreate(e) {
    e.preventDefault();
    if (!writeable) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      let config = {};
      if (configJson.trim()) {
        config = JSON.parse(configJson);
      }
      const res = await createKnowledgeSyncJob(collectionId, {
        connector_type: connector,
        config,
      });
      setLastJob(res);
      setMessage(`Sync job created (${res?.job_id || "ok"}).`);
    } catch (err) {
      setError(err.message || "Failed to create sync job");
    } finally {
      setBusy(false);
    }
  }

  async function handleRun() {
    if (!writeable || !lastJob?.job_id) return;
    setBusy(true);
    setError("");
    try {
      const res = await runKnowledgeSyncJob(lastJob.job_id);
      setMessage(
        `Sync finished — ${res?.documents_added ?? res?.added ?? 0} added, ${res?.errors?.length ?? 0} errors.`,
      );
    } catch (err) {
      setError(err.message || "Sync run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="workspace-card mt-6 rounded-2xl p-5">
      <h2 className="text-sm font-semibold text-neutral-900">Sync connectors</h2>
      <p className="mt-1 text-xs text-neutral-500">
        Pull documents from S3, Git, or webhook sources into this collection.
      </p>

      {error && <WorkspaceAlert type="error" className="mt-3">{error}</WorkspaceAlert>}
      {message && <WorkspaceAlert type="success" className="mt-3">{message}</WorkspaceAlert>}

      <form onSubmit={handleCreate} className="mt-4 space-y-3">
        <label className="block text-xs font-medium text-neutral-600">
          Connector
          <select
            className="input-field mt-1 w-full"
            value={connector}
            disabled={!writeable || busy}
            onChange={(e) => setConnector(e.target.value)}
          >
            {CONNECTORS.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-neutral-600">
          Config (JSON)
          <textarea
            className="input-field mt-1 w-full font-mono text-[11px]"
            rows={4}
            disabled={!writeable || busy}
            value={configJson}
            onChange={(e) => setConfigJson(e.target.value)}
            placeholder='{"bucket":"my-bucket","prefix":"docs/"}'
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button type="submit" className="btn-primary text-xs" disabled={!writeable || busy}>
            {busy ? "Working…" : "Create sync job"}
          </button>
          {lastJob?.job_id && (
            <button
              type="button"
              className="btn-secondary text-xs"
              disabled={!writeable || busy}
              onClick={handleRun}
            >
              Run now
            </button>
          )}
        </div>
      </form>
    </section>
  );
}
