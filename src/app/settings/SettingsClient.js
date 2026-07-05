"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { getUserInfo, changePassword } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import {
  getAllLlm,
  getAssistantLlmConfig,
  getKnowledgeLlmConfig,
  getLlmSettings,
  updateLlmSettings,
  createLlmProvider,
  deleteLlmProvider,
  activateLlmProvider,
} from "@/lib/api/llm";
import { getApiBaseUrl } from "@/lib/api/config";
import { getTeamMembers, updateMemberRole, downloadAuditExport, getAuditEvents } from "@/lib/api/analytics";
import { getWorkspaceQuotas, updateWorkspaceQuotas, getActiveWorkspaceId } from "@/lib/api/workspaces";
import { getOAuthProviders } from "@/lib/api/oauth";
import { createApiKey, deleteApiKey, listApiKeys } from "@/lib/api/apiKeys";
import { resetSetup } from "@/lib/setup/storage";

const ease = [0.16, 1, 0.3, 1];

export default function SettingsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [llmServers, setLlmServers] = useState([]);
  const [assistantCfg, setAssistantCfg] = useState(null);
  const [knowledgeCfg, setKnowledgeCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [team, setTeam] = useState([]);
  const [teamBusy, setTeamBusy] = useState(null);
  const [provider, setProvider] = useState(null);
  const [providerSaving, setProviderSaving] = useState(false);
  const [providerMsg, setProviderMsg] = useState("");
  const [exportBusy, setExportBusy] = useState(false);
  const [pwdCurrent, setPwdCurrent] = useState("");
  const [pwdNew, setPwdNew] = useState("");
  const [pwdConfirm, setPwdConfirm] = useState("");
  const [pwdBusy, setPwdBusy] = useState(false);
  const [pwdMsg, setPwdMsg] = useState("");
  const [ssoProviders, setSsoProviders] = useState([]);
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [newProvider, setNewProvider] = useState({
    name: "",
    provider_type: "openai",
    base_url: "https://api.openai.com/v1",
    api_key: "",
    chat_model: "gpt-4o-mini",
    embedding_model: "text-embedding-3-small",
  });
  const [providerBusy, setProviderBusy] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [apiKeyName, setApiKeyName] = useState("");
  const [apiKeyBusy, setApiKeyBusy] = useState(false);
  const [newApiKey, setNewApiKey] = useState("");
  const [apiKeyMsg, setApiKeyMsg] = useState("");
  const [auditEvents, setAuditEvents] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [quotas, setQuotas] = useState(null);
  const [quotaBusy, setQuotaBusy] = useState(false);
  const [quotaMsg, setQuotaMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [h, llm, aCfg, kCfg] = await Promise.all([
        checkBackendHealth(),
        getAllLlm().catch(() => []),
        getAssistantLlmConfig().catch(() => null),
        getKnowledgeLlmConfig().catch(() => null),
      ]);
      setHealth(h);
      setLlmServers(Array.isArray(llm) ? llm : llm?.data || []);
      setAssistantCfg(aCfg);
      setKnowledgeCfg(kCfg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  useEffect(() => {
    if (user?.role === "admin") {
      getTeamMembers()
        .then((m) => setTeam(Array.isArray(m) ? m : m?.data || []))
        .catch(() => setTeam([]));
      getLlmSettings()
        .then(setProvider)
        .catch(() => setProvider(null));
      getOAuthProviders()
        .then((list) => setSsoProviders(Array.isArray(list) ? list : []))
        .catch(() => setSsoProviders([]));
      listApiKeys()
        .then((rows) => setApiKeys(Array.isArray(rows) ? rows : rows?.data || []))
        .catch(() => setApiKeys([]));
      setAuditLoading(true);
      getAuditEvents(14, 80)
        .then((rows) => setAuditEvents(Array.isArray(rows) ? rows : []))
        .catch(() => setAuditEvents([]))
        .finally(() => setAuditLoading(false));
      const wid = getActiveWorkspaceId();
      if (wid) {
        getWorkspaceQuotas(wid).then(setQuotas).catch(() => setQuotas(null));
      }
    }
  }, [user]);

  async function handleRoleChange(memberId, role) {
    setTeamBusy(memberId);
    try {
      await updateMemberRole(memberId, role);
      const m = await getTeamMembers();
      setTeam(Array.isArray(m) ? m : m?.data || []);
    } finally {
      setTeamBusy(null);
    }
  }

  function handleRerunSetup() {
    resetSetup();
    router.push("/setup");
  }

  async function handleSaveQuotas(e) {
    e.preventDefault();
    const wid = getActiveWorkspaceId();
    if (!wid || !quotas) return;
    setQuotaBusy(true);
    setQuotaMsg("");
    try {
      const updated = await updateWorkspaceQuotas(wid, {
        eval_runs_monthly_limit: Number(quotas.eval_runs_monthly_limit) || 0,
        finetune_jobs_monthly_limit: Number(quotas.finetune_jobs_monthly_limit) || 0,
      });
      setQuotas(updated);
      setQuotaMsg("Workspace quotas saved.");
    } catch (err) {
      setQuotaMsg(err.message || "Save failed");
    } finally {
      setQuotaBusy(false);
    }
  }

  async function handleCreateApiKey(e) {
    e.preventDefault();
    setApiKeyBusy(true);
    setApiKeyMsg("");
    setNewApiKey("");
    try {
      const res = await createApiKey(apiKeyName.trim() || "API key");
      setNewApiKey(res?.key || "");
      setApiKeyName("");
      const rows = await listApiKeys();
      setApiKeys(Array.isArray(rows) ? rows : rows?.data || []);
      setApiKeyMsg("Copy your key now — it won't be shown again.");
    } catch (err) {
      setApiKeyMsg(err.message || "Failed to create key");
    } finally {
      setApiKeyBusy(false);
    }
  }

  async function handleDeleteApiKey(id) {
    if (!window.confirm("Revoke this API key? Integrations using it will stop working.")) return;
    setApiKeyBusy(true);
    setApiKeyMsg("");
    try {
      await deleteApiKey(id);
      const rows = await listApiKeys();
      setApiKeys(Array.isArray(rows) ? rows : rows?.data || []);
      setApiKeyMsg("API key revoked.");
    } catch (err) {
      setApiKeyMsg(err.message || "Delete failed");
    } finally {
      setApiKeyBusy(false);
    }
  }

  async function handleSaveProvider(e) {
    e.preventDefault();
    if (!provider) return;
    setProviderSaving(true);
    setProviderMsg("");
    try {
      const updated = await updateLlmSettings({
        chat_model: provider.chat_model,
        embedding_model: provider.embedding_model,
        openai_base_url: provider.openai_base_url,
      });
      setProvider(updated);
      setProviderMsg("Active provider settings saved.");
      await load();
    } catch (err) {
      setProviderMsg(err.message || "Save failed");
    } finally {
      setProviderSaving(false);
    }
  }

  async function reloadProviderSettings() {
    const updated = await getLlmSettings();
    setProvider(updated);
    return updated;
  }

  async function handleActivateProvider(id) {
    setProviderBusy(id);
    setProviderMsg("");
    try {
      await activateLlmProvider(id);
      await reloadProviderSettings();
      setProviderMsg("Active provider updated.");
      await load();
    } catch (err) {
      setProviderMsg(err.message || "Activate failed");
    } finally {
      setProviderBusy(null);
    }
  }

  async function handleDeleteProvider(id) {
    if (!window.confirm("Delete this provider? Stored API key will be removed.")) return;
    setProviderBusy(id);
    setProviderMsg("");
    try {
      await deleteLlmProvider(id);
      await reloadProviderSettings();
      setProviderMsg("Provider deleted.");
      await load();
    } catch (err) {
      setProviderMsg(err.message || "Delete failed");
    } finally {
      setProviderBusy(null);
    }
  }

  async function handleAddProvider(e) {
    e.preventDefault();
    setProviderSaving(true);
    setProviderMsg("");
    try {
      await createLlmProvider({ ...newProvider, activate: true });
      await reloadProviderSettings();
      setShowAddProvider(false);
      setNewProvider({
        name: "",
        provider_type: "openai",
        base_url: "https://api.openai.com/v1",
        api_key: "",
        chat_model: "gpt-4o-mini",
        embedding_model: "text-embedding-3-small",
      });
      setProviderMsg("Provider added and activated.");
      await load();
    } catch (err) {
      setProviderMsg(err.message || "Add provider failed");
    } finally {
      setProviderSaving(false);
    }
  }

  function applyProviderType(typeId) {
    const meta = (provider?.provider_types || []).find((t) => t.id === typeId);
    if (!meta) return;
    setNewProvider((p) => ({
      ...p,
      provider_type: typeId,
      base_url: meta.base_url,
      chat_model: meta.default_chat,
      embedding_model: meta.default_embedding || p.embedding_model,
    }));
  }

  async function handleExportAudit() {
    setExportBusy(true);
    try {
      await downloadAuditExport(30);
    } catch (err) {
      setProviderMsg(err.message || "Export failed");
    } finally {
      setExportBusy(false);
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    setPwdMsg("");
    if (pwdNew !== pwdConfirm) {
      setPwdMsg("New passwords do not match");
      return;
    }
    if (pwdNew.length < 6) {
      setPwdMsg("New password must be at least 6 characters");
      return;
    }
    setPwdBusy(true);
    try {
      await changePassword(pwdCurrent, pwdNew);
      setPwdCurrent("");
      setPwdNew("");
      setPwdConfirm("");
      setPwdMsg("Password updated successfully.");
    } catch (err) {
      setPwdMsg(err.message || "Password change failed");
    } finally {
      setPwdBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="relative flex min-h-screen items-center justify-center">
        <WorkspaceLiveBackground />
        <span className="relative z-10 text-neutral-500">Loading…</span>
      </div>
    );
  }

  const modelCount = llmServers.reduce(
    (n, s) => n + (s.models?.length || s.model_list?.length || 0),
    0
  );

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-12">
          <WorkspaceHero
            eyebrow="Workspace"
            title="Settings &"
            titleHighlight="health"
            description="Monitor API status, model providers, and workspace configuration."
          />

          <div className="mt-10 space-y-5">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
            >
              <h2 className="text-lg font-semibold tracking-tight">System health</h2>
              <dl className="mt-5 space-y-4 text-sm">
                <div className="flex justify-between gap-4 border-b border-black/[0.04] pb-3">
                  <dt className="text-neutral-500">API URL</dt>
                  <dd className="truncate font-mono text-xs text-neutral-800">{getApiBaseUrl()}</dd>
                </div>
                <div className="flex justify-between gap-4 border-b border-black/[0.04] pb-3">
                  <dt className="text-neutral-500">API status</dt>
                  <dd>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${
                        health?.ok ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${health?.ok ? "bg-emerald-500" : "bg-red-500"}`} />
                      {loading ? "…" : health?.ok ? "Online" : "Offline"}
                    </span>
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-neutral-500">Signed in as</dt>
                  <dd className="font-medium">{user.user_name}</dd>
                </div>
              </dl>
              <button type="button" onClick={load} className="mt-5 text-sm font-semibold hover:underline">
                Refresh status
              </button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.14, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
            >
              <h2 className="text-lg font-semibold tracking-tight">Models</h2>
              <p className="mt-1 text-sm text-neutral-500">
                {loading
                  ? "Loading…"
                  : `${llmServers.length} provider${llmServers.length !== 1 ? "s" : ""}, ${modelCount} model${modelCount !== 1 ? "s" : ""}`}
              </p>
              {!loading && llmServers.length > 0 && (
                <ul className="mt-5 space-y-2">
                  {llmServers.slice(0, 8).map((server) => (
                    <li
                      key={server.id || server.name}
                      className="flex items-center justify-between rounded-xl border border-white/60 bg-white/55 px-4 py-2.5 text-sm backdrop-blur-sm"
                    >
                      <span className="font-medium">{server.name || server.server_name}</span>
                      <span className="text-xs text-neutral-400">
                        {(server.models || server.model_list || []).length} models
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-5 space-y-1 text-xs text-neutral-500">
                {assistantCfg && (
                  <p>
                    Assistant default:{" "}
                    <span className="font-medium text-neutral-800">
                      {assistantCfg?.llm_model?.model_name || assistantCfg?.model_name || "Not set"}
                    </span>
                  </p>
                )}
                {knowledgeCfg && (
                  <p>
                    Knowledge embedding:{" "}
                    <span className="font-medium text-neutral-800">
                      {knowledgeCfg?.embedding_model?.model_name || "Not set"}
                    </span>
                  </p>
                )}
              </div>
            </motion.div>

            {user.role === "admin" && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, ease }}
                className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
              >
                <h2 className="text-lg font-semibold tracking-tight">Single sign-on</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  OAuth providers enabled on the server appear on the login page.
                </p>
                {ssoProviders.length === 0 ? (
                  <p className="mt-4 text-sm text-neutral-500">
                    None configured. Set <code className="text-xs">GOOGLE_CLIENT_ID</code> /{" "}
                    <code className="text-xs">MICROSOFT_CLIENT_ID</code> in backend env.
                  </p>
                ) : (
                  <ul className="mt-4 space-y-2">
                    {ssoProviders.map((p) => (
                      <li
                        key={p.id}
                        className="flex items-center justify-between rounded-xl border border-white/60 bg-white/55 px-4 py-2.5 text-sm"
                      >
                        <span className="font-medium">{p.label}</span>
                        <span className="text-[10px] font-bold uppercase text-emerald-600">Active</span>
                      </li>
                    ))}
                  </ul>
                )}
              </motion.div>
            )}

            {user.role === "admin" && provider && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.16, ease }}
                className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">Model providers</h2>
                    <p className="mt-1 text-sm text-neutral-500">
                      Store API keys encrypted in the vault. Switch active provider for chat and embeddings.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowAddProvider((v) => !v)}
                    className="workspace-btn-ghost !py-2 text-sm"
                  >
                    {showAddProvider ? "Cancel" : "+ Add provider"}
                  </button>
                </div>

                {(provider.providers || []).length > 0 && (
                  <ul className="mt-5 space-y-2">
                    {(provider.providers || []).map((p) => (
                      <li
                        key={p.id}
                        className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border px-4 py-3 ${
                          p.is_active ? "border-emerald-200 bg-emerald-50/60" : "border-black/[0.06] bg-white/60"
                        }`}
                      >
                        <div className="min-w-0">
                          <p className="font-medium text-neutral-900">
                            {p.name}
                            {p.is_active && (
                              <span className="ml-2 text-[10px] font-bold uppercase text-emerald-600">Active</span>
                            )}
                          </p>
                          <p className="text-xs text-neutral-500">
                            {p.provider_type} · {p.chat_model}
                            {p.api_key_hint ? ` · key ${p.api_key_hint}` : p.api_key_configured ? " · key set" : " · no key"}
                          </p>
                        </div>
                        <div className="flex shrink-0 gap-2">
                          {!p.is_active && (
                            <button
                              type="button"
                              disabled={providerBusy === p.id}
                              onClick={() => handleActivateProvider(p.id)}
                              className="workspace-btn-ghost !px-2.5 !py-1.5 text-xs"
                            >
                              Activate
                            </button>
                          )}
                          <button
                            type="button"
                            disabled={providerBusy === p.id}
                            onClick={() => handleDeleteProvider(p.id)}
                            className="workspace-btn-ghost workspace-btn-danger !px-2.5 !py-1.5 text-xs"
                          >
                            Delete
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}

                {showAddProvider && (
                  <form onSubmit={handleAddProvider} className="mt-5 space-y-4 rounded-xl border border-black/[0.06] bg-white/50 p-4">
                    <label className="block text-sm font-medium">
                      Name
                      <input
                        value={newProvider.name}
                        onChange={(e) => setNewProvider((p) => ({ ...p, name: e.target.value }))}
                        className="input-field mt-1.5 w-full"
                        placeholder="Production OpenAI"
                        required
                      />
                    </label>
                    <label className="block text-sm font-medium">
                      Provider type
                      <select
                        value={newProvider.provider_type}
                        onChange={(e) => applyProviderType(e.target.value)}
                        className="input-field mt-1.5 w-full"
                      >
                        {(provider.provider_types || []).map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="block text-sm font-medium">
                      Base URL
                      <input
                        value={newProvider.base_url}
                        onChange={(e) => setNewProvider((p) => ({ ...p, base_url: e.target.value }))}
                        className="input-field mt-1.5 w-full font-mono text-xs"
                      />
                    </label>
                    <label className="block text-sm font-medium">
                      API key
                      <input
                        type="password"
                        value={newProvider.api_key}
                        onChange={(e) => setNewProvider((p) => ({ ...p, api_key: e.target.value }))}
                        className="input-field mt-1.5 w-full font-mono text-xs"
                        placeholder="sk-…"
                        autoComplete="off"
                      />
                    </label>
                    <label className="block text-sm font-medium">
                      Chat model
                      <input
                        value={newProvider.chat_model}
                        onChange={(e) => setNewProvider((p) => ({ ...p, chat_model: e.target.value }))}
                        className="input-field mt-1.5 w-full"
                      />
                    </label>
                    <button type="submit" disabled={providerSaving} className="btn-primary disabled:opacity-50">
                      {providerSaving ? "Adding…" : "Save to vault"}
                    </button>
                  </form>
                )}

                <form onSubmit={handleSaveProvider} className="mt-6 space-y-4 border-t border-black/[0.06] pt-6">
                  <h3 className="text-sm font-semibold text-neutral-800">Active provider models</h3>
                  <div>
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${
                        provider.api_key_configured
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {provider.api_key_configured ? "API key configured" : "Demo mode (no API key)"}
                    </span>
                    {provider.provider_name && (
                      <span className="ml-2 text-xs text-neutral-500">{provider.provider_name}</span>
                    )}
                  </div>
                  <label className="block text-sm font-medium">
                    Base URL
                    <input
                      value={provider.openai_base_url || ""}
                      onChange={(e) => setProvider((p) => ({ ...p, openai_base_url: e.target.value }))}
                      className="input-field mt-1.5 w-full font-mono text-xs"
                    />
                  </label>
                  <label className="block text-sm font-medium">
                    Chat model
                    <select
                      value={provider.chat_model || ""}
                      onChange={(e) => setProvider((p) => ({ ...p, chat_model: e.target.value }))}
                      className="input-field mt-1.5 w-full"
                    >
                      {(provider.chat_models || []).map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-medium">
                    Embedding model
                    <select
                      value={provider.embedding_model || ""}
                      onChange={(e) => setProvider((p) => ({ ...p, embedding_model: e.target.value }))}
                      className="input-field mt-1.5 w-full"
                    >
                      {(provider.embedding_models || []).map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </label>
                  {providerMsg && <p className="text-sm text-neutral-600">{providerMsg}</p>}
                  <button type="submit" disabled={providerSaving} className="btn-primary disabled:opacity-50">
                    {providerSaving ? "Saving…" : "Save active provider"}
                  </button>
                </form>
              </motion.div>
            )}

            {user.role === "admin" && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.17, ease }}
                className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
              >
                <h2 className="text-lg font-semibold tracking-tight">Audit log</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  Export workspace usage events (chat, workflow runs) as CSV for the last 30 days.
                </p>
                <button
                  type="button"
                  onClick={handleExportAudit}
                  disabled={exportBusy}
                  className="workspace-btn-ghost mt-5 disabled:opacity-50"
                >
                  {exportBusy ? "Exporting…" : "Download audit CSV"}
                </button>
                <div className="mt-6">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">Recent activity</p>
                  {auditLoading ? (
                    <p className="mt-3 text-sm text-neutral-500">Loading events…</p>
                  ) : auditEvents.length === 0 ? (
                    <p className="mt-3 text-sm text-neutral-500">No events in the last 14 days.</p>
                  ) : (
                    <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto">
                      {auditEvents.map((ev, i) => (
                        <li key={`${ev.timestamp}-${i}`} className="rounded-lg border border-black/[0.05] bg-white/50 px-3 py-2 text-xs">
                          <div className="flex justify-between gap-2">
                            <span className="font-semibold text-neutral-800">{ev.event_type}</span>
                            <span className="shrink-0 text-neutral-400">
                              {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : "—"}
                            </span>
                          </div>
                          <p className="mt-0.5 text-neutral-500">
                            {ev.user}
                            {ev.resource_id ? ` · ${ev.resource_id}` : ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </motion.div>
            )}

            <motion.form
              onSubmit={handleChangePassword}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.19, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
            >
              <h2 className="text-lg font-semibold tracking-tight">Password</h2>
              <p className="mt-1 text-sm text-neutral-500">Change your account password.</p>
              <div className="mt-5 space-y-4">
                <label className="block text-sm font-medium">
                  Current password
                  <input
                    type="password"
                    value={pwdCurrent}
                    onChange={(e) => setPwdCurrent(e.target.value)}
                    className="input-field mt-1.5 w-full"
                    autoComplete="current-password"
                  />
                </label>
                <label className="block text-sm font-medium">
                  New password
                  <input
                    type="password"
                    value={pwdNew}
                    onChange={(e) => setPwdNew(e.target.value)}
                    className="input-field mt-1.5 w-full"
                    autoComplete="new-password"
                  />
                </label>
                <label className="block text-sm font-medium">
                  Confirm new password
                  <input
                    type="password"
                    value={pwdConfirm}
                    onChange={(e) => setPwdConfirm(e.target.value)}
                    className="input-field mt-1.5 w-full"
                    autoComplete="new-password"
                  />
                </label>
              </div>
              {pwdMsg && <p className="mt-4 text-sm text-neutral-600">{pwdMsg}</p>}
              <button type="submit" disabled={pwdBusy} className="btn-primary mt-5 disabled:opacity-50">
                {pwdBusy ? "Updating…" : "Update password"}
              </button>
            </motion.form>

            {user.role === "admin" && quotas && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.13, ease }}
                className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
              >
                <h2 className="text-lg font-semibold tracking-tight">Workspace quotas</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  Monthly limits for evaluation runs and fine-tune jobs (0 = unlimited).
                </p>
                <form onSubmit={handleSaveQuotas} className="mt-5 grid gap-4 sm:grid-cols-2">
                  <label className="block text-sm font-medium">
                    Eval runs / month
                    <input
                      type="number"
                      min="0"
                      value={quotas.eval_runs_monthly_limit || 0}
                      onChange={(e) => setQuotas((q) => ({ ...q, eval_runs_monthly_limit: e.target.value }))}
                      className="input-field mt-1.5 w-full"
                    />
                    <span className="mt-1 block text-xs text-neutral-400">Used: {quotas.eval_runs_this_month || 0}</span>
                  </label>
                  <label className="block text-sm font-medium">
                    Fine-tune jobs / month
                    <input
                      type="number"
                      min="0"
                      value={quotas.finetune_jobs_monthly_limit || 0}
                      onChange={(e) => setQuotas((q) => ({ ...q, finetune_jobs_monthly_limit: e.target.value }))}
                      className="input-field mt-1.5 w-full"
                    />
                    <span className="mt-1 block text-xs text-neutral-400">Used: {quotas.finetune_jobs_this_month || 0}</span>
                  </label>
                  {quotaMsg && <p className="sm:col-span-2 text-sm text-neutral-600">{quotaMsg}</p>}
                  <button type="submit" disabled={quotaBusy} className="btn-primary sm:col-span-2 disabled:opacity-50">
                    {quotaBusy ? "Saving…" : "Save quotas"}
                  </button>
                </form>
              </motion.div>
            )}

            {user.role === "admin" && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.14, ease }}
                className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
              >
                <h2 className="text-lg font-semibold tracking-tight">API keys</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  Programmatic access for scripts and integrations. Send{" "}
                  <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">X-Api-Key: nf_…</code> on requests.
                </p>

                {newApiKey && (
                  <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/80 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">New key — copy now</p>
                    <code className="mt-2 block break-all rounded-lg bg-white px-3 py-2 text-xs font-mono text-neutral-800">
                      {newApiKey}
                    </code>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard?.writeText(newApiKey)}
                      className="workspace-btn-ghost mt-3 !py-1.5 text-xs"
                    >
                      Copy to clipboard
                    </button>
                  </div>
                )}

                {apiKeyMsg && <p className="mt-3 text-sm text-neutral-600">{apiKeyMsg}</p>}

                <form onSubmit={handleCreateApiKey} className="mt-5 flex flex-wrap gap-2">
                  <input
                    value={apiKeyName}
                    onChange={(e) => setApiKeyName(e.target.value)}
                    placeholder="Key label (e.g. CI pipeline)"
                    className="input-field min-w-[200px] flex-1"
                  />
                  <button type="submit" disabled={apiKeyBusy} className="btn-primary disabled:opacity-50">
                    {apiKeyBusy ? "Creating…" : "Create key"}
                  </button>
                </form>

                <ul className="mt-5 space-y-2">
                  {apiKeys.length === 0 ? (
                    <li className="text-sm text-neutral-500">No API keys yet.</li>
                  ) : (
                    apiKeys.map((k) => (
                      <li
                        key={k.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/60 bg-white/55 px-4 py-2.5"
                      >
                        <div>
                          <p className="text-sm font-medium">{k.name}</p>
                          <p className="font-mono text-[11px] text-neutral-400">
                            {k.key_prefix}… · {k.create_time ? new Date(k.create_time).toLocaleDateString() : "—"}
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={apiKeyBusy}
                          onClick={() => handleDeleteApiKey(k.id)}
                          className="workspace-btn-ghost workspace-btn-danger !px-2.5 !py-1.5 text-xs"
                        >
                          Revoke
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              </motion.div>
            )}

            {user.role === "admin" && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, ease }}
                className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
              >
                <h2 className="text-lg font-semibold tracking-tight">Team & roles</h2>
                <p className="mt-1 text-sm text-neutral-500">Manage workspace access for your team.</p>
                <ul className="mt-5 space-y-2">
                  {team.map((member) => (
                    <li
                      key={member.user_id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/60 bg-white/55 px-4 py-2.5 backdrop-blur-sm"
                    >
                      <div>
                        <p className="text-sm font-medium">{member.user_name}</p>
                        <p className="text-[11px] text-neutral-400">ID {member.user_id}</p>
                      </div>
                      <select
                        value={member.role || "editor"}
                        disabled={teamBusy === member.user_id}
                        onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                        className="rounded-lg border border-black/10 bg-white px-2.5 py-1.5 text-xs font-semibold"
                      >
                        <option value="admin">Admin</option>
                        <option value="editor">Editor</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.18, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 sm:p-7"
            >
              <h2 className="text-lg font-semibold tracking-tight">Onboarding</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Re-run the setup wizard to create a new starter assistant from templates.
              </p>
              <button type="button" onClick={handleRerunSetup} className="workspace-btn-ghost mt-5">
                Re-run setup wizard
              </button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22, ease }}
              className="workspace-panel rounded-[1.75rem] p-6 text-center sm:p-7"
            >
              <p className="text-sm text-neutral-500">Quick links</p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <Link href="/apps" className="workspace-btn-ghost">Apps</Link>
                <Link href="/knowledge" className="workspace-btn-ghost">Knowledge</Link>
                <Link href="/workflows" className="workspace-btn-ghost">Workflows</Link>
                <Link href="/chat" className="workspace-btn-ghost">Chat</Link>
              </div>
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  );
}
