"use client";

import { useEffect, useState } from "react";
import { listCredentials } from "@/lib/api/credentials";

const HTTP_AUTH_MAP = {
  custom: { category: "custom", kind: "custom" },
  youtube: { category: "youtube", kind: "youtube_api" },
  google: { category: "google", kind: "google_oauth" },
  shopify: { category: "shopify", kind: "shopify_admin" },
  outlook: { category: "outlook", kind: "microsoft_graph" },
};

const NOTIFY_CHANNEL_MAP = {
  telegram: { category: "telegram", kind: "telegram_bot" },
  email: { category: "email", kind: "gmail_smtp" },
  slack: { category: "slack", kind: "slack_webhook" },
  discord: { category: "discord", kind: "discord_webhook" },
  webhook: { category: "webhook", kind: "generic_webhook" },
};

export function resolveVaultFilter(nodeType, data = {}) {
  const ntype = String(nodeType || "").toLowerCase();
  if (ntype === "http") {
    const auth = (data.auth || "custom").toLowerCase();
    return HTTP_AUTH_MAP[auth] || HTTP_AUTH_MAP.custom;
  }
  if (ntype === "notify") {
    const channel = (data.channel || "telegram").toLowerCase();
    return NOTIFY_CHANNEL_MAP[channel] || NOTIFY_CHANNEL_MAP.telegram;
  }
  if (ntype === "jira") return { category: "jira", kind: "jira_cloud" };
  if (ntype === "github") return { category: "github", kind: "github_pat" };
  if (ntype === "linear") return { category: "linear", kind: "linear_api" };
  if (ntype === "api_node" || ntype === "component_node") {
    return { category: "custom", kind: "custom" };
  }
  return null;
}

export default function VaultCredentialSelect({
  nodeType,
  nodeData = {},
  value = "",
  onChange,
  readOnly = false,
  label = "Credential (vault)",
  vaultCategory,
  vaultKind,
  className = "mt-4",
}) {
  const [opts, setOpts] = useState([]);
  const filter = vaultCategory
    ? { category: vaultCategory, kind: vaultKind }
    : resolveVaultFilter(nodeType, nodeData);

  useEffect(() => {
    if (!filter?.category) {
      setOpts([]);
      return;
    }
    const params = { category: filter.category };
    if (filter.kind) params.kind = filter.kind;
    listCredentials(params)
      .then((rows) => setOpts(Array.isArray(rows) ? rows : []))
      .catch(() => setOpts([]));
  }, [filter?.category, filter?.kind]);

  return (
    <label className={`${className} block`}>
      <span className="text-xs font-semibold text-neutral-600">{label}</span>
      <select
        value={value || ""}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={readOnly}
        className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
      >
        <option value="">Default for this provider</option>
        {opts.map((e) => (
          <option key={e.id} value={e.id}>
            {e.label} ({e.kind}){e.is_default ? " · default" : ""}
          </option>
        ))}
      </select>
      <p className="mt-1 text-[11px] text-neutral-400">
        Manage named accounts in{" "}
        <a href="/credentials" className="underline">Credentials</a>
        {" "}or paste secrets in chat.
      </p>
    </label>
  );
}
