"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import SettingsNav, { SettingsStatCard } from "@/components/settings/SettingsNav";
import SettingsSection, {
  SettingsRow,
  SettingsListItem,
  SettingsEmpty,
  SettingsMessage,
} from "@/components/settings/SettingsSection";
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
import { createAbRoute, deleteAbRoute, listAbRoutes, updateAbRoute } from "@/lib/api/finetune";
import { resetSetup } from "@/lib/setup/storage";

const SECTION_ICONS = {
  health: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  ),
  models: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5M2 12l10 5 10-5" />
    </svg>
  ),
  sso: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3" />
    </svg>
  ),
  password: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  ),
  audit: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </svg>
  ),
  keys: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
    </svg>
  ),
  team: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  setup: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  ),
  ab: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
    </svg>
  ),
  quota: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M12 20V10M18 20V4M6 20v-4" />
    </svg>
  ),
};

function SettingsLoading() {
  return <WorkspaceLoading message="Loading settings…" />;
}

export default function SettingsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [llmServers, setLlmServers] = useState([]);
  const [assistantCfg, setAssistantCfg] = useState(null);
  const [knowledgeCfg, setKnowledgeCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
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
  const [abRoutes, setAbRoutes] = useState([]);
  const [abBase, setAbBase] = useState("");
  const [abVariant, setAbVariant] = useState("");
  const [abTraffic, setAbTraffic] = useState(50);
  const [abBusy, setAbBusy] = useState(false);
  const [abMsg, setAbMsg] = useState("");

  const isAdmin = user?.role === "admin";

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
    if (!isAdmin) return;
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
    listAbRoutes()
      .then((rows) => setAbRoutes(Array.isArray(rows) ? rows : rows?.data || []))
      .catch(() => setAbRoutes([]));
  }, [isAdmin]);

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

  async function handleCreateAbRoute(e) {
    e.preventDefault();
    if (!abBase.trim() || !abVariant.trim()) return;
    setAbBusy(true);
    setAbMsg("");
    try {
      await createAbRoute({
        base_model: abBase.trim(),
        variant_model: abVariant.trim(),
        variant_traffic_pct: Number(abTraffic) || 50,
        enabled: true,
      });
      const rows = await listAbRoutes();
      setAbRoutes(Array.isArray(rows) ? rows : rows?.data || []);
      setAbBase("");
      setAbVariant("");
      setAbTraffic(50);
      setAbMsg("A/B route created.");
    } catch (err) {
      setAbMsg(err.message || "Create failed");
    } finally {
      setAbBusy(false);
    }
  }

  async function handleToggleAbRoute(route) {
    setAbBusy(true);
    try {
      await updateAbRoute(route.id, { enabled: !route.enabled });
      const rows = await listAbRoutes();
      setAbRoutes(Array.isArray(rows) ? rows : rows?.data || []);
    } catch (err) {
      setAbMsg(err.message || "Update failed");
    } finally {
      setAbBusy(false);
    }
  }

  async function handleDeleteAbRoute(id) {
    setAbBusy(true);
    try {
      await deleteAbRoute(id);
      setAbRoutes((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setAbMsg(err.message || "Delete failed");
    } finally {
      setAbBusy(false);
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

  const modelCount = useMemo(
    () => llmServers.reduce((n, s) => n + (s.models?.length || s.model_list?.length || 0), 0),
    [llmServers]
  );

  const assistantModel =
    assistantCfg?.llm_model?.model_name || assistantCfg?.model_name || "Not set";
  const embeddingModel = knowledgeCfg?.embedding_model?.model_name || "Not set";

  if (!user) {
    return <SettingsLoading />;
  }

  return (
    <div className="settings-shell relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">
          <WorkspaceHero
            eyebrow="Workspace"
            title="Settings &"
            titleHighlight="configuration"
            description="Monitor API health, manage models, security, and workspace access from one place."
            badge={
              health?.ok ? (
                <span className="workspace-badge-live">System online</span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-red-200/80 bg-red-50/90 px-2.5 py-0.5 text-[10px] font-bold uppercase text-red-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                  Offline
                </span>
              )
            }
            actions={
              <button
                type="button"
                onClick={load}
                disabled={loading}
                className="workspace-btn-ghost disabled:opacity-50"
              >
                {loading ? "Refreshing…" : "Refresh status"}
              </button>
            }
          >
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <SettingsStatCard
                label="API status"
                value={loading ? "…" : health?.ok ? "Online" : "Offline"}
                hint={getApiBaseUrl()}
                status={loading ? undefined : health?.ok ? "online" : "offline"}
              />
              <SettingsStatCard
                label="Models"
                value={loading ? "…" : String(modelCount)}
                hint={`${llmServers.length} provider${llmServers.length !== 1 ? "s" : ""} connected`}
              />
              <SettingsStatCard
                label="Signed in as"
                value={user.user_name}
                hint={isAdmin ? "Administrator" : user.role || "Member"}
              />
              {isAdmin ? (
                <SettingsStatCard
                  label="Team"
                  value={String(team.length)}
                  hint={`${apiKeys.length} API key${apiKeys.length !== 1 ? "s" : ""} active`}
                />
              ) : (
                <SettingsStatCard label="Role" value={user.role || "Member"} hint="Contact admin for elevated access" />
              )}
            </div>
          </WorkspaceHero>

          <div className="settings-layout mt-8 lg:mt-10">
            <aside className="settings-sidebar shrink-0">
              <SettingsNav activeTab={activeTab} onChange={setActiveTab} isAdmin={isAdmin} />
            </aside>

            <div className="settings-content min-w-0 space-y-5">
              {activeTab === "overview" && (
                <>
                  <SettingsSection
                    icon={SECTION_ICONS.health}
                    title="System health"
                    description="Backend connectivity and your current session."
                    delay={0.05}
                  >
                    <dl className="settings-kv-list space-y-3">
                      <SettingsRow label="API URL" value={getApiBaseUrl()} mono />
                      <SettingsRow
                        label="API status"
                        value={
                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${
                              health?.ok ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                            }`}
                          >
                            <span className={`h-1.5 w-1.5 rounded-full ${health?.ok ? "bg-emerald-500" : "bg-red-500"}`} />
                            {loading ? "Checking…" : health?.ok ? "Online" : "Offline"}
                          </span>
                        }
                      />
                      <SettingsRow label="Account" value={user.user_name} border={false} />
                    </dl>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.models}
                    title="Model overview"
                    description="Registered providers and default models for assistants and knowledge."
                    delay={0.08}
                  >
                    <p className="text-sm text-neutral-600">
                      {loading
                        ? "Loading providers…"
                        : `${llmServers.length} provider${llmServers.length !== 1 ? "s" : ""}, ${modelCount} model${modelCount !== 1 ? "s" : ""}`}
                    </p>
                    {!loading && llmServers.length > 0 && (
                      <ul className="mt-4 space-y-2">
                        {llmServers.slice(0, 8).map((server) => (
                          <SettingsListItem key={server.id || server.name}>
                            <span className="text-sm font-medium">{server.name || server.server_name}</span>
                            <span className="text-xs text-neutral-400">
                              {(server.models || server.model_list || []).length} models
                            </span>
                          </SettingsListItem>
                        ))}
                      </ul>
                    )}
                    <div className="settings-defaults mt-5 grid gap-3 sm:grid-cols-2">
                      <div className="settings-default-card rounded-xl border border-black/[0.05] bg-white/55 px-4 py-3">
                        <p className="text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">Assistant</p>
                        <p className="mt-1 truncate text-sm font-medium text-neutral-900">{assistantModel}</p>
                      </div>
                      <div className="settings-default-card rounded-xl border border-black/[0.05] bg-white/55 px-4 py-3">
                        <p className="text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">Embedding</p>
                        <p className="mt-1 truncate text-sm font-medium text-neutral-900">{embeddingModel}</p>
                      </div>
                    </div>
                    {isAdmin && (
                      <button
                        type="button"
                        onClick={() => setActiveTab("models")}
                        className="workspace-btn-ghost mt-5 !py-2 text-sm"
                      >
                        Manage providers →
                      </button>
                    )}
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.setup}
                    title="Onboarding"
                    description="Re-run the setup wizard to create a new starter assistant from templates."
                    delay={0.1}
                  >
                    <button type="button" onClick={handleRerunSetup} className="workspace-btn-ghost">
                      Re-run setup wizard
                    </button>
                  </SettingsSection>

                  <SettingsSection
                    title="Quick links"
                    description="Jump to other workspace modules."
                    delay={0.12}
                    className="text-center"
                  >
                    <div className="flex flex-wrap justify-center gap-2">
                      <Link href="/apps" className="workspace-btn-ghost">Apps</Link>
                      <Link href="/knowledge" className="workspace-btn-ghost">Knowledge</Link>
                      <Link href="/workflows" className="workspace-btn-ghost">Workflows</Link>
                      <Link href="/chat" className="workspace-btn-ghost">Chat</Link>
                      {isAdmin && (
                        <Link href="/developer" className="workspace-btn-ghost">Developer</Link>
                      )}
                    </div>
                  </SettingsSection>
                </>
              )}

              {activeTab === "security" && (
                <>
                  <SettingsSection
                    icon={SECTION_ICONS.password}
                    title="Password"
                    description="Update your account password."
                    delay={0.05}
                  >
                    <form onSubmit={handleChangePassword} className="settings-form-grid">
                      <label className="settings-label">
                        Current password
                        <input
                          type="password"
                          value={pwdCurrent}
                          onChange={(e) => setPwdCurrent(e.target.value)}
                          className="input-field mt-1.5 w-full"
                          autoComplete="current-password"
                        />
                      </label>
                      <label className="settings-label">
                        New password
                        <input
                          type="password"
                          value={pwdNew}
                          onChange={(e) => setPwdNew(e.target.value)}
                          className="input-field mt-1.5 w-full"
                          autoComplete="new-password"
                        />
                      </label>
                      <label className="settings-label sm:col-span-2">
                        Confirm new password
                        <input
                          type="password"
                          value={pwdConfirm}
                          onChange={(e) => setPwdConfirm(e.target.value)}
                          className="input-field mt-1.5 w-full"
                          autoComplete="new-password"
                        />
                      </label>
                      <SettingsMessage type={pwdMsg.includes("success") ? "success" : pwdMsg ? "error" : "info"}>
                        {pwdMsg}
                      </SettingsMessage>
                      <button type="submit" disabled={pwdBusy} className="btn-primary sm:col-span-2 disabled:opacity-50">
                        {pwdBusy ? "Updating…" : "Update password"}
                      </button>
                    </form>
                  </SettingsSection>

                  {isAdmin && (
                    <SettingsSection
                      icon={SECTION_ICONS.sso}
                      title="Single sign-on"
                      description="OAuth providers enabled on the server appear on the login page."
                      delay={0.08}
                    >
                      {ssoProviders.length === 0 ? (
                        <SettingsEmpty>
                          None configured. Set <code className="text-xs">GOOGLE_CLIENT_ID</code> /{" "}
                          <code className="text-xs">MICROSOFT_CLIENT_ID</code> in backend env.
                        </SettingsEmpty>
                      ) : (
                        <ul className="space-y-2">
                          {ssoProviders.map((p) => (
                            <SettingsListItem key={p.id} active>
                              <span className="text-sm font-medium">{p.label}</span>
                              <span className="text-[10px] font-bold uppercase text-emerald-600">Active</span>
                            </SettingsListItem>
                          ))}
                        </ul>
                      )}
                    </SettingsSection>
                  )}
                </>
              )}

              {activeTab === "models" && isAdmin && (
                <>
                  {provider && (
                    <SettingsSection
                      icon={SECTION_ICONS.models}
                      title="Model providers"
                      description="Store API keys encrypted in the vault. Switch active provider for chat and embeddings."
                      delay={0.05}
                      actions={
                        <button
                          type="button"
                          onClick={() => setShowAddProvider((v) => !v)}
                          className="workspace-btn-ghost !py-2 text-sm"
                        >
                          {showAddProvider ? "Cancel" : "+ Add provider"}
                        </button>
                      }
                    >
                      {(provider.providers || []).length > 0 ? (
                        <ul className="space-y-2">
                          {(provider.providers || []).map((p) => (
                            <SettingsListItem key={p.id} active={p.is_active}>
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-neutral-900">
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
                            </SettingsListItem>
                          ))}
                        </ul>
                      ) : (
                        <SettingsEmpty>No providers yet. Add one to connect your LLM API.</SettingsEmpty>
                      )}

                      {showAddProvider && (
                        <form onSubmit={handleAddProvider} className="settings-form-card mt-5 space-y-4">
                          <label className="settings-label">
                            Name
                            <input
                              value={newProvider.name}
                              onChange={(e) => setNewProvider((p) => ({ ...p, name: e.target.value }))}
                              className="input-field mt-1.5 w-full"
                              placeholder="Production OpenAI"
                              required
                            />
                          </label>
                          <label className="settings-label">
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
                          <label className="settings-label">
                            Base URL
                            <input
                              value={newProvider.base_url}
                              onChange={(e) => setNewProvider((p) => ({ ...p, base_url: e.target.value }))}
                              className="input-field mt-1.5 w-full font-mono text-xs"
                            />
                          </label>
                          <label className="settings-label">
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
                          <label className="settings-label">
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

                      <form onSubmit={handleSaveProvider} className="settings-form-card mt-6 space-y-4 border-t border-black/[0.06] pt-6">
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
                        <label className="settings-label">
                          Base URL
                          <input
                            value={provider.openai_base_url || ""}
                            onChange={(e) => setProvider((p) => ({ ...p, openai_base_url: e.target.value }))}
                            className="input-field mt-1.5 w-full font-mono text-xs"
                          />
                        </label>
                        <label className="settings-label">
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
                        <label className="settings-label">
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
                        <SettingsMessage type={providerMsg.includes("saved") || providerMsg.includes("added") || providerMsg.includes("updated") || providerMsg.includes("deleted") ? "success" : providerMsg ? "error" : "info"}>
                          {providerMsg}
                        </SettingsMessage>
                        <button type="submit" disabled={providerSaving} className="btn-primary disabled:opacity-50">
                          {providerSaving ? "Saving…" : "Save active provider"}
                        </button>
                      </form>
                    </SettingsSection>
                  )}

                  {quotas && (
                    <SettingsSection
                      icon={SECTION_ICONS.quota}
                      title="Workspace quotas"
                      description="Monthly limits for evaluation runs and fine-tune jobs (0 = unlimited)."
                      delay={0.08}
                    >
                      <form onSubmit={handleSaveQuotas} className="settings-form-grid">
                        <label className="settings-label">
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
                        <label className="settings-label">
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
                        <SettingsMessage type={quotaMsg.includes("saved") ? "success" : quotaMsg ? "error" : "info"}>
                          {quotaMsg}
                        </SettingsMessage>
                        <button type="submit" disabled={quotaBusy} className="btn-primary sm:col-span-2 disabled:opacity-50">
                          {quotaBusy ? "Saving…" : "Save quotas"}
                        </button>
                      </form>
                    </SettingsSection>
                  )}

                  <SettingsSection
                    icon={SECTION_ICONS.ab}
                    title="A/B model routing"
                    description="Split traffic between a base and variant model for chat and workflow LLM nodes."
                    delay={0.1}
                  >
                    <form onSubmit={handleCreateAbRoute} className="settings-form-grid sm:grid-cols-3">
                      <label className="settings-label">
                        Base model
                        <input
                          value={abBase}
                          onChange={(e) => setAbBase(e.target.value)}
                          placeholder="gpt-4o-mini"
                          className="input-field mt-1.5 w-full"
                        />
                      </label>
                      <label className="settings-label">
                        Variant model
                        <input
                          value={abVariant}
                          onChange={(e) => setAbVariant(e.target.value)}
                          placeholder="ft:gpt-4o-mini:custom"
                          className="input-field mt-1.5 w-full"
                        />
                      </label>
                      <label className="settings-label">
                        Variant traffic %
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={abTraffic}
                          onChange={(e) => setAbTraffic(e.target.value)}
                          className="input-field mt-1.5 w-full"
                        />
                      </label>
                      <SettingsMessage type={abMsg.includes("created") ? "success" : abMsg ? "error" : "info"}>
                        {abMsg}
                      </SettingsMessage>
                      <button type="submit" disabled={abBusy} className="btn-primary sm:col-span-3 disabled:opacity-50">
                        {abBusy ? "Saving…" : "Add route"}
                      </button>
                    </form>
                    <ul className="mt-6 space-y-2">
                      {abRoutes.length === 0 ? (
                        <SettingsEmpty>No A/B routes configured.</SettingsEmpty>
                      ) : (
                        abRoutes.map((route) => (
                          <SettingsListItem key={route.id}>
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-neutral-900">
                                {route.base_model} → {route.variant_model}
                              </p>
                              <p className="mt-0.5 text-xs text-neutral-500">
                                {route.variant_traffic_pct}% variant · {route.enabled ? "Active" : "Paused"}
                              </p>
                            </div>
                            <div className="flex shrink-0 gap-2">
                              <button
                                type="button"
                                disabled={abBusy}
                                onClick={() => handleToggleAbRoute(route)}
                                className="workspace-btn-ghost !py-1.5 text-xs"
                              >
                                {route.enabled ? "Pause" : "Enable"}
                              </button>
                              <button
                                type="button"
                                disabled={abBusy}
                                onClick={() => handleDeleteAbRoute(route.id)}
                                className="workspace-btn-ghost workspace-btn-danger !py-1.5 text-xs"
                              >
                                Delete
                              </button>
                            </div>
                          </SettingsListItem>
                        ))
                      )}
                    </ul>
                  </SettingsSection>
                </>
              )}

              {activeTab === "integrations" && isAdmin && (
                <>
                  <SettingsSection
                    icon={SECTION_ICONS.keys}
                    title="API keys"
                    description={
                      <>
                        Programmatic access for scripts and integrations. Send{" "}
                        <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">X-Api-Key: nf_…</code> on requests.{" "}
                        <Link href="/developer" className="font-medium text-neutral-800 underline-offset-2 hover:underline">
                          Open API playground
                        </Link>
                      </>
                    }
                    delay={0.05}
                  >
                    {newApiKey && (
                      <div className="settings-key-reveal rounded-xl border border-amber-200 bg-amber-50/80 p-4">
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

                    <SettingsMessage type={apiKeyMsg.includes("Copy") || apiKeyMsg.includes("revoked") ? "success" : apiKeyMsg ? "error" : "info"}>
                      {apiKeyMsg}
                    </SettingsMessage>

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
                        <SettingsEmpty>No API keys yet.</SettingsEmpty>
                      ) : (
                        apiKeys.map((k) => (
                          <SettingsListItem key={k.id}>
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
                          </SettingsListItem>
                        ))
                      )}
                    </ul>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.audit}
                    title="Audit log"
                    description="Export workspace usage events (chat, workflow runs) as CSV for the last 30 days."
                    delay={0.08}
                    actions={
                      <button
                        type="button"
                        onClick={handleExportAudit}
                        disabled={exportBusy}
                        className="workspace-btn-ghost !py-2 text-sm disabled:opacity-50"
                      >
                        {exportBusy ? "Exporting…" : "Download CSV"}
                      </button>
                    }
                  >
                    <p className="workspace-section-label">Recent activity</p>
                    {auditLoading ? (
                      <p className="mt-3 text-sm text-neutral-500">Loading events…</p>
                    ) : auditEvents.length === 0 ? (
                      <SettingsEmpty>No events in the last 14 days.</SettingsEmpty>
                    ) : (
                      <ul className="settings-audit-list mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
                        {auditEvents.map((ev, i) => (
                          <li key={`${ev.timestamp}-${i}`} className="settings-audit-item rounded-xl border border-black/[0.05] bg-white/50 px-3 py-2.5 text-xs">
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
                  </SettingsSection>
                </>
              )}

              {activeTab === "team" && isAdmin && (
                <SettingsSection
                  icon={SECTION_ICONS.team}
                  title="Team & roles"
                  description="Manage workspace access for your team."
                  delay={0.05}
                >
                  {team.length === 0 ? (
                    <SettingsEmpty>No team members found.</SettingsEmpty>
                  ) : (
                    <ul className="space-y-2">
                      {team.map((member) => (
                        <SettingsListItem key={member.user_id}>
                          <div>
                            <p className="text-sm font-medium">{member.user_name}</p>
                            <p className="text-[11px] text-neutral-400">ID {member.user_id}</p>
                          </div>
                          <select
                            value={member.role || "editor"}
                            disabled={teamBusy === member.user_id}
                            onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                            className="settings-role-select rounded-lg border border-black/10 bg-white px-2.5 py-1.5 text-xs font-semibold"
                          >
                            <option value="admin">Admin</option>
                            <option value="editor">Editor</option>
                            <option value="viewer">Viewer</option>
                          </select>
                        </SettingsListItem>
                      ))}
                    </ul>
                  )}
                </SettingsSection>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
