"use client";

import { useState } from "react";
import { bindSlackEvents } from "@/lib/api/integrations";

export default function WorkflowSlackPanel({ workflowId, workflowStatus, publicBaseUrl = "" }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [eventsUrl, setEventsUrl] = useState("");

  async function handleBind() {
    if (!workflowId) return;
    setBusy(true);
    setMsg("");
    try {
      const res = await bindSlackEvents({
        workflow_id: workflowId,
        public_base_url: publicBaseUrl || undefined,
      });
      setEventsUrl(res?.events_url || "");
      setMsg(res?.detail || "Slack Events URL bound.");
    } catch (err) {
      setMsg(err.message || "Bind failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-6 rounded-xl border border-black/[0.06] bg-white/70 p-4">
      <p className="text-sm font-semibold text-neutral-900">Slack Events API</p>
      <p className="mt-1 text-xs text-neutral-500">
        Bind this published workflow as the Slack bot inbound target. Add bot token + signing secret in Settings,
        then set this URL as Slack Event Subscriptions Request URL.
      </p>
      {workflowStatus !== 1 && (
        <p className="mt-2 text-xs text-amber-700">Publish the workflow before binding Slack events.</p>
      )}
      <button
        type="button"
        disabled={busy || workflowStatus !== 1}
        onClick={handleBind}
        className="btn-secondary mt-3 text-xs disabled:opacity-50"
      >
        {busy ? "Binding…" : "Bind Slack events"}
      </button>
      {eventsUrl && (
        <p className="mt-2 break-all font-mono text-[10px] text-neutral-600">{eventsUrl}</p>
      )}
      {msg && <p className="mt-2 text-xs text-neutral-500">{msg}</p>}
    </div>
  );
}
