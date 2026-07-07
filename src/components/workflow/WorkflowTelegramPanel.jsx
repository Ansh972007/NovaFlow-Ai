"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  getTelegramSetup,
  registerTelegramWebhook,
  getIntegrationSettings,
  getTelegramWebhookStatus,
} from "@/lib/api/integrations";

export default function WorkflowTelegramPanel({ workflowId, published }) {
  const [setup, setSetup] = useState(null);
  const [status, setStatus] = useState(null);
  const [publicBase, setPublicBase] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const reload = useCallback(async () => {
    if (!workflowId || !published) return;
    try {
      const [s, st, settings] = await Promise.all([
        getTelegramSetup(workflowId).catch(() => null),
        getTelegramWebhookStatus().catch(() => null),
        getIntegrationSettings().catch(() => null),
      ]);
      setSetup(s);
      setStatus(st);
      if (settings?.public_base_url) setPublicBase(settings.public_base_url);
      else if (s?.public_base_url) setPublicBase(s.public_base_url);
    } catch {
      setSetup(null);
    }
  }, [workflowId, published]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleRegister() {
    setBusy(true);
    setMsg("");
    try {
      const res = await registerTelegramWebhook({
        workflow_id: workflowId,
        public_base_url: publicBase.trim() || undefined,
      });
      setMsg(res?.detail || "Telegram webhook registered.");
      await reload();
    } catch (err) {
      setMsg(err.message || "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  if (!published) return null;

  const configured = setup?.telegram_configured;
  const registered = setup?.webhook_registered;
  const inboundUrl = setup?.webhook_url || "";

  return (
    <div className="mt-4 border-t border-black/[0.06] pt-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-700">Telegram inbound</p>
      <p className="mt-1 text-[10px] text-neutral-500">
        Messages to your bot trigger this workflow. Outbound replies use the <strong>notify</strong> node.
      </p>

      {!configured && (
        <p className="mt-2 rounded-lg bg-amber-50 px-2.5 py-2 text-[10px] text-amber-800">
          Bot not configured.{" "}
          <Link href="/settings" className="font-semibold underline">
            Settings → Integrations
          </Link>
        </p>
      )}

      {inboundUrl && (
        <code className="mt-2 block break-all rounded-lg bg-neutral-50 px-2 py-1.5 text-[10px] font-mono text-neutral-700">
          POST {inboundUrl}
        </code>
      )}

      <label className="mt-3 block">
        <span className="text-[10px] font-medium text-neutral-500">Public API base URL</span>
        <input
          value={publicBase}
          onChange={(e) => setPublicBase(e.target.value)}
          placeholder="https://api.yourdomain.com"
          className="input-field mt-1 w-full font-mono text-[10px]"
        />
        <span className="mt-0.5 block text-[10px] text-neutral-400">
          Required for production — Telegram must reach your server
        </span>
      </label>

      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || !configured}
          onClick={handleRegister}
          className="rounded-lg bg-teal-700 px-3 py-1.5 text-[10px] font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Registering…" : registered ? "Re-register webhook" : "Register webhook"}
        </button>
        {inboundUrl && (
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(inboundUrl)}
            className="text-[10px] font-semibold text-neutral-600 hover:text-neutral-900"
          >
            Copy URL
          </button>
        )}
      </div>

      {registered && (
        <p className="mt-2 text-[10px] text-emerald-700">
          Webhook active for this workflow
          {setup?.stored_webhook_url ? ` · ${setup.stored_webhook_url.slice(0, 48)}…` : ""}
        </p>
      )}

      {status?.live?.url && (
        <p className="mt-1 text-[10px] text-neutral-500">
          Telegram reports: {status.live.url.slice(0, 60)}
          {status.live.url.length > 60 ? "…" : ""}
        </p>
      )}

      {msg && <p className="mt-2 text-[10px] text-neutral-600">{msg}</p>}
    </div>
  );
}
