"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import CopyUriBox from "@/components/workspace/CopyUriBox";
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
  const autoRegisterAttempted = useRef(false);

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

  async function handleRegister(silent = false) {
    setBusy(true);
    if (!silent) setMsg("");
    try {
      const res = await registerTelegramWebhook({
        workflow_id: workflowId,
        public_base_url: publicBase.trim() || undefined,
      });
      if (!silent) {
        setMsg(res?.detail || "Telegram webhook registered.");
      }
      await reload();
      return res;
    } catch (err) {
      if (!silent) setMsg(err.message || "Registration failed");
      return null;
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!published || !setup || busy || autoRegisterAttempted.current) return;
    if (setup.telegram_configured && !setup.webhook_registered) {
      autoRegisterAttempted.current = true;
      handleRegister(true);
    }
  }, [published, setup, busy]);

  if (!published) return null;

  const configured = setup?.telegram_configured;
  const registered = setup?.webhook_registered;
  const inboundUrl = setup?.webhook_url || "";
  const botUsername = setup?.bot_username || "";

  return (
    <div className="mt-4 border-t border-black/[0.06] pt-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-700">Telegram inbound</p>
      <p className="mt-1 text-[10px] text-neutral-500">
        Messages to your bot trigger this workflow. Reply with a <strong>notify</strong> node (
        <code className="text-[9px]">to: {"{{chat_id}}"}</code>).
      </p>

      {botUsername ? (
        <p className="mt-2 text-[10px] text-emerald-800">
          Bot: <strong>@{botUsername}</strong>
        </p>
      ) : null}

      {!configured && (
        <p className="mt-2 rounded-lg bg-amber-50 px-2.5 py-2 text-[10px] text-amber-800">
          Bot not configured.{" "}
          <Link href="/credentials?tab=messaging" className="font-semibold underline">
            Credentials → Messaging
          </Link>
          — paste bot token + label, then save.
        </p>
      )}

      {inboundUrl ? (
        <CopyUriBox label="Inbound webhook URL" uri={`POST ${inboundUrl}`} className="mt-2" />
      ) : null}

      <label className="mt-3 block">
        <span className="text-[10px] font-medium text-neutral-500">Public API base URL</span>
        <input
          value={publicBase}
          onChange={(e) => setPublicBase(e.target.value)}
          placeholder="https://api.yourdomain.com"
          className="input-field mt-1 w-full font-mono text-[10px]"
        />
        <span className="mt-0.5 block text-[10px] text-neutral-400">
          Required for production — Telegram must reach your server (use ngrok locally)
        </span>
      </label>

      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || !configured}
          onClick={() => handleRegister(false)}
          className="rounded-lg bg-teal-700 px-3 py-1.5 text-[10px] font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Registering…" : registered ? "Re-register webhook" : "Register webhook"}
        </button>
      </div>

      {registered ? (
        <p className="mt-2 text-[10px] text-emerald-700">
          Webhook active — publishing also registers automatically
        </p>
      ) : configured ? (
        <p className="mt-2 text-[10px] text-neutral-500">Webhook registers on publish, or click Register above.</p>
      ) : null}

      {status?.live?.url ? (
        <p className="mt-1 text-[10px] text-neutral-500">
          Telegram reports: {status.live.url.slice(0, 60)}
          {status.live.url.length > 60 ? "…" : ""}
        </p>
      ) : null}

      {msg ? <p className="mt-2 text-[10px] text-neutral-600">{msg}</p> : null}
    </div>
  );
}
