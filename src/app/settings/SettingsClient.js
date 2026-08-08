"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import SettingsNav, { SettingsStatCard } from "@/components/settings/SettingsNav";
import SettingsSection, {
  SettingsRow,
  SettingsListItem,
  SettingsEmpty,
  SettingsMessage,
} from "@/components/settings/SettingsSection";
import { getUserInfo, changePassword } from "@/lib/api/auth";
import { useWorkspaceAccess } from "@/lib/auth/workspaceAccess";
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
  verifyLlmProvider,
} from "@/lib/api/llm";
import { getApiBaseUrl } from "@/lib/api/config";
import { downloadAuditExport, getAuditEvents } from "@/lib/api/analytics";
import {
  getWorkspaceQuotas,
  updateWorkspaceQuotas,
  getActiveWorkspaceId,
  ensureActiveWorkspace,
  listWorkspaceMembers,
  updateWorkspaceMemberRole,
  inviteWorkspaceMember,
  listWorkspaceInvites,
  revokeWorkspaceInvite,
  workspaceCanAdmin,
  workspaceCanEdit,
  workspaceCanManageApiKeys,
} from "@/lib/api/workspaces";
import { getOAuthProviders } from "@/lib/api/oauth";
import { createApiKey, deleteApiKey, listApiKeys } from "@/lib/api/apiKeys";
import {
  getIntegrationSettings,
  updateIntegrationSettings,
  getIntegrationHealth,
  verifyTelegramBot,
  testEmailIntegration,
  testNotify,
  startGmailOAuth,
  disconnectGmailOAuth,
  verifyJira,
  testSlackIntegration,
  verifyGithub,
  testDiscordIntegration,
  verifyLinear,
} from "@/lib/api/integrations";
import { createAbRoute, deleteAbRoute, listAbRoutes, updateAbRoute } from "@/lib/api/finetune";
import { getOAuthSetup } from "@/lib/api/credentials";
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
  telegram: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  ),
  email: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M22 6l-10 7L2 6" />
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

function isPlatformAdminUser(user) {
  if (!user) return false;
  const role = String(user.role || "").toLowerCase();
  return role === "admin" || role === "super_admin" || user.is_admin === true;
}

export default function SettingsClient() {
  const router = useRouter();
  const { role: workspaceRole, readOnly: workspaceReadOnly } = useWorkspaceAccess();
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [llmServers, setLlmServers] = useState([]);
  const [assistantCfg, setAssistantCfg] = useState(null);
  const [knowledgeCfg, setKnowledgeCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [modelLoadWarning, setModelLoadWarning] = useState("");
  const [adminLoadError, setAdminLoadError] = useState("");
  const [teamLoadError, setTeamLoadError] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [team, setTeam] = useState([]);
  const [invites, setInvites] = useState([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [inviteMsg, setInviteMsg] = useState("");
  const [teamMsg, setTeamMsg] = useState("");
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

  const [integrationSettings, setIntegrationSettings] = useState(null);
  const [integrationHealth, setIntegrationHealth] = useState(null);
  const [tgToken, setTgToken] = useState("");
  const [tgChatId, setTgChatId] = useState("");
  const [tgUsername, setTgUsername] = useState("");
  const [smtpHost, setSmtpHost] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [gmailPreset, setGmailPreset] = useState(true);
  const [jiraBaseUrl, setJiraBaseUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraApiToken, setJiraApiToken] = useState("");
  const [slackWebhook, setSlackWebhook] = useState("");
  const [slackChannel, setSlackChannel] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [githubOwner, setGithubOwner] = useState("");
  const [githubRepo, setGithubRepo] = useState("");
  const [discordWebhook, setDiscordWebhook] = useState("");
  const [discordChannel, setDiscordChannel] = useState("");
  const [linearApiKey, setLinearApiKey] = useState("");
  const [linearTeamId, setLinearTeamId] = useState("");
  const [slackBotToken, setSlackBotToken] = useState("");
  const [slackSigningSecret, setSlackSigningSecret] = useState("");
  const [integrationBusy, setIntegrationBusy] = useState(false);
  const [integrationMsg, setIntegrationMsg] = useState("");
  const [oauthSetup, setOauthSetup] = useState(null);
  const [publicBaseUrl, setPublicBaseUrl] = useState("");

  const readOnly = workspaceReadOnly;
  const canManageWorkspace = workspaceCanAdmin(workspaceRole);
  const isPlatformAdmin = isPlatformAdminUser(user);
  const canManageApiKeys = workspaceCanManageApiKeys(workspaceRole);
  const canEditWorkspace = workspaceCanEdit(workspaceRole);
  const searchParams = useSearchParams();

  const applyIntegrationSettings = useCallback((s) => {
    setIntegrationSettings(s);
    if (s?.telegram) {
      setTgChatId(s.telegram.default_chat_id || "");
      setTgUsername(s.telegram.bot_username || "");
    }
    if (s?.email) {
      setGmailPreset(!!s.email.gmail_preset);
      setSmtpHost(s.email.smtp_host || "smtp.gmail.com");
      setSmtpPort(s.email.smtp_port || 587);
      setSmtpUser(s.email.smtp_user || "");
      setSmtpFrom(s.email.smtp_from || "");
    }
    if (s?.jira) {
      setJiraBaseUrl(s.jira.base_url || "");
      setJiraEmail(s.jira.email || "");
    }
    if (s?.slack) {
      setSlackChannel(s.slack.default_channel || "");
    }
    if (s?.github) {
      setGithubOwner(s.github.owner || "");
      setGithubRepo(s.github.repo || "");
    }
    if (s?.discord) {
      setDiscordChannel(s.discord.default_channel || "");
    }
    if (s?.linear) {
      setLinearTeamId(s.linear.team_id || "");
    }
    setPublicBaseUrl(s?.public_base_url || "");
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    setModelLoadWarning("");
    try {
      const h = await checkBackendHealth();
      setHealth(h);
      const llmPromise = getAllLlm().catch((err) => {
        setModelLoadWarning(err.message || "Failed to load model providers");
        return [];
      });
      const [llm, aCfg, kCfg] = await Promise.all([
        llmPromise,
        getAssistantLlmConfig().catch(() => null),
        getKnowledgeLlmConfig().catch(() => null),
      ]);
      setLlmServers(Array.isArray(llm) ? llm : llm?.data || []);
      setAssistantCfg(aCfg);
      setKnowledgeCfg(kCfg);
    } catch (err) {
      setLoadError(err.message || "Failed to load settings");
      setHealth(null);
      setLlmServers([]);
      setAssistantCfg(null);
      setKnowledgeCfg(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        if (!u) {
          router.replace("/login");
          return;
        }
        try {
          await ensureActiveWorkspace();
        } catch {
          /* optional */
        }
        setUser(u);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const reloadWorkspaceTeam = useCallback(async () => {
    const wid = getActiveWorkspaceId();
    if (!wid) {
      setTeam([]);
      setInvites([]);
      setTeamLoadError("");
      return;
    }
    setTeamLoadError("");
    try {
      const members = await listWorkspaceMembers(wid);
      setTeam(Array.isArray(members) ? members : []);
      try {
        const pending = await listWorkspaceInvites(wid);
        setInvites(Array.isArray(pending) ? pending : []);
      } catch (invErr) {
        setInvites([]);
        setTeamLoadError(invErr.message || "Failed to load pending invites");
      }
    } catch (err) {
      setTeam([]);
      setInvites([]);
      setTeamLoadError(err.message || "Failed to load team");
    }
  }, []);

  const reloadAdminSections = useCallback(async () => {
    setAdminLoadError("");
    const wid = getActiveWorkspaceId();

    if (canManageWorkspace) {
      await reloadWorkspaceTeam();
      try {
        const [settings, health] = await Promise.all([
          getIntegrationSettings(),
          getIntegrationHealth(),
        ]);
        applyIntegrationSettings(settings);
        setIntegrationHealth(health);
      } catch (err) {
        setAdminLoadError(err.message || "Failed to load workspace settings");
      }
      if (wid) {
        try {
          setQuotas(await getWorkspaceQuotas(wid));
        } catch {
          setQuotas(null);
        }
      }
      try {
        setOauthSetup(await getOAuthSetup());
      } catch {
        setOauthSetup(null);
      }
    }

    if (isPlatformAdmin) {
      try {
        setProvider(await getLlmSettings());
      } catch {
        setProvider(null);
      }
      try {
        const list = await getOAuthProviders();
        setSsoProviders(Array.isArray(list) ? list : []);
      } catch {
        setSsoProviders([]);
      }
      setAuditLoading(true);
      try {
        const rows = await getAuditEvents(14, 80);
        setAuditEvents(Array.isArray(rows) ? rows : []);
      } catch {
        setAuditEvents([]);
      } finally {
        setAuditLoading(false);
      }
      try {
        const rows = await listAbRoutes();
        setAbRoutes(Array.isArray(rows) ? rows : rows?.data || []);
      } catch {
        setAbRoutes([]);
      }
    }

    if (canManageApiKeys) {
      try {
        const rows = await listApiKeys();
        setApiKeys(Array.isArray(rows) ? rows : rows?.data || []);
      } catch {
        setApiKeys([]);
      }
    }
  }, [
    canManageWorkspace,
    isPlatformAdmin,
    canManageApiKeys,
    reloadWorkspaceTeam,
    applyIntegrationSettings,
  ]);

  useEffect(() => {
    if (!user) return;
    if (!canManageWorkspace && !isPlatformAdmin && !canManageApiKeys) return;
    reloadAdminSections();
  }, [user, canManageWorkspace, isPlatformAdmin, canManageApiKeys, reloadAdminSections]);

  useEffect(() => {
    const tab = searchParams?.get("tab");
    if (tab === "models" || tab === "integrations" || tab === "ai") {
      router.replace("/credentials");
      return;
    }
    if (tab && ["overview", "security", "team"].includes(tab)) {
      setActiveTab(tab);
    }
    if (searchParams?.get("must_change") === "1") {
      setActiveTab("security");
      setPwdMsg("You must set a new password before using NovaFlow.");
    }
    const gmail = searchParams?.get("gmail");
    if (!gmail) return;
    if (gmail === "connected") setIntegrationMsg("Gmail connected with Google OAuth.");
    if (gmail === "error") {
      setIntegrationMsg(`Gmail OAuth failed: ${searchParams.get("msg") || "unknown error"}`);
    }
  }, [searchParams, router]);

  useEffect(() => {
    if (activeTab === "models" || activeTab === "integrations") {
      setActiveTab("overview");
    }
  }, [activeTab]);

  async function handleRoleChange(memberId, role) {
    const wid = getActiveWorkspaceId();
    if (!wid || readOnly || !canManageWorkspace) return;
    setTeamBusy(memberId);
    setTeamMsg("");
    try {
      await updateWorkspaceMemberRole(wid, memberId, role);
      await reloadWorkspaceTeam();
      setTeamMsg("Role updated.");
    } catch (err) {
      setTeamMsg(err.message || "Role update failed");
    } finally {
      setTeamBusy(null);
    }
  }

  async function handleInvite(e) {
    e.preventDefault();
    const wid = getActiveWorkspaceId();
    if (!wid || !inviteEmail.trim() || readOnly || !canManageWorkspace) return;
    setInviteMsg("");
    setTeamMsg("");
    try {
      await inviteWorkspaceMember(wid, { email: inviteEmail.trim(), role: inviteRole });
      setInviteEmail("");
      setInviteMsg("Invitation sent.");
      await reloadWorkspaceTeam();
    } catch (err) {
      setInviteMsg(err.message || "Invite failed");
    }
  }

  async function handleRevokeInvite(inviteId) {
    const wid = getActiveWorkspaceId();
    if (!wid || readOnly || !canManageWorkspace) return;
    setTeamBusy(inviteId);
    setTeamMsg("");
    try {
      await revokeWorkspaceInvite(wid, inviteId);
      await reloadWorkspaceTeam();
      setTeamMsg("Invitation revoked.");
    } catch (err) {
      setTeamMsg(err.message || "Revoke failed");
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

  async function reloadIntegrations() {
    const [s, h] = await Promise.all([
      getIntegrationSettings().catch(() => null),
      getIntegrationHealth().catch(() => null),
    ]);
    if (s) {
      setIntegrationSettings(s);
      setTgChatId(s.telegram?.default_chat_id || "");
      setTgUsername(s.telegram?.bot_username || "");
      if (s.email) {
        setGmailPreset(!!s.email.gmail_preset);
        setSmtpHost(s.email.smtp_host || "smtp.gmail.com");
        setSmtpPort(s.email.smtp_port || 587);
        setSmtpUser(s.email.smtp_user || "");
        setSmtpFrom(s.email.smtp_from || "");
      }
      if (s.jira) {
        setJiraBaseUrl(s.jira.base_url || "");
        setJiraEmail(s.jira.email || "");
      }
      if (s.slack) {
        setSlackChannel(s.slack.default_channel || "");
      }
      if (s.github) {
        setGithubOwner(s.github.owner || "");
        setGithubRepo(s.github.repo || "");
      }
      if (s.discord) {
        setDiscordChannel(s.discord.default_channel || "");
      }
      if (s.linear) {
        setLinearTeamId(s.linear.team_id || "");
      }
      setPublicBaseUrl(s.public_base_url || "");
    }
    setIntegrationHealth(h);
  }

  async function handleSaveIntegrations(e) {
    e?.preventDefault();
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const payload = {
        public_base_url: publicBaseUrl.trim(),
        telegram: {
          default_chat_id: tgChatId.trim(),
          bot_username: tgUsername.trim(),
        },
        email: {
          gmail_preset: gmailPreset,
          smtp_host: gmailPreset ? "smtp.gmail.com" : smtpHost.trim(),
          smtp_port: Number(smtpPort) || 587,
          smtp_user: smtpUser.trim(),
          smtp_from: smtpFrom.trim() || smtpUser.trim(),
        },
      };
      if (tgToken.trim()) payload.telegram.bot_token = tgToken.trim();
      if (smtpPassword.trim()) payload.email.smtp_password = smtpPassword.trim();
      await updateIntegrationSettings(payload);
      setTgToken("");
      setSmtpPassword("");
      await reloadIntegrations();
      setIntegrationMsg("Integration settings saved to workspace.");
    } catch (err) {
      setIntegrationMsg(err.message || "Save failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleVerifyTelegram() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const res = await verifyTelegramBot(tgToken.trim() ? { bot_token: tgToken.trim() } : {});
      const bot = res?.bot;
      setIntegrationMsg(bot ? `Connected: @${bot.username}` : "Telegram bot verified.");
      if (bot?.username) setTgUsername(bot.username);
      await reloadIntegrations();
    } catch (err) {
      setIntegrationMsg(err.message || "Telegram verification failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleTestTelegram() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      await testNotify({
        channel: "telegram",
        to: tgChatId.trim(),
        message: "NovaFlow Telegram test from Settings",
        bot_token: tgToken.trim() || undefined,
      });
      setIntegrationMsg("Telegram test message sent.");
    } catch (err) {
      setIntegrationMsg(err.message || "Telegram test failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleTestEmail() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      await testEmailIntegration({
        to: smtpUser.trim() || smtpFrom.trim(),
        subject: "NovaFlow Gmail/SMTP test",
        message: "Your workspace email integration is working.",
      });
      setIntegrationMsg("Test email sent.");
    } catch (err) {
      setIntegrationMsg(err.message || "Email test failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleClearTelegramToken() {
    setIntegrationBusy(true);
    try {
      await updateIntegrationSettings({ telegram: { clear_token: true } });
      await reloadIntegrations();
      setIntegrationMsg("Telegram token cleared.");
    } catch (err) {
      setIntegrationMsg(err.message || "Clear failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleClearSmtpPassword() {
    setIntegrationBusy(true);
    try {
      await updateIntegrationSettings({ email: { clear_password: true } });
      await reloadIntegrations();
      setIntegrationMsg("SMTP password cleared.");
    } catch (err) {
      setIntegrationMsg(err.message || "Clear failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleConnectGmailOAuth() {
    setIntegrationMsg("");
    startGmailOAuth();
  }

  async function handleDisconnectGmailOAuth() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      await disconnectGmailOAuth();
      await reloadIntegrations();
      setIntegrationMsg("Gmail OAuth disconnected — SMTP mode restored.");
    } catch (err) {
      setIntegrationMsg(err.message || "Disconnect failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleSaveJira(e) {
    e.preventDefault();
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const payload = {
        jira: {
          base_url: jiraBaseUrl.trim(),
          email: jiraEmail.trim(),
        },
      };
      if (jiraApiToken.trim()) payload.jira.api_token = jiraApiToken.trim();
      await updateIntegrationSettings(payload);
      setJiraApiToken("");
      await reloadIntegrations();
      setIntegrationMsg("Jira settings saved.");
    } catch (err) {
      setIntegrationMsg(err.message || "Failed to save Jira settings");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleVerifyJira() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const res = await verifyJira();
      setIntegrationMsg(res?.detail || "Jira verified.");
      await reloadIntegrations();
    } catch (err) {
      setIntegrationMsg(err.message || "Jira verification failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleClearJiraToken() {
    setIntegrationBusy(true);
    try {
      await updateIntegrationSettings({ jira: { clear_token: true } });
      await reloadIntegrations();
      setIntegrationMsg("Jira API token cleared.");
    } catch (err) {
      setIntegrationMsg(err.message || "Clear failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleSaveSlack(e) {
    e.preventDefault();
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const payload = { slack: { default_channel: slackChannel.trim() } };
      if (slackWebhook.trim()) payload.slack.webhook_url = slackWebhook.trim();
      await updateIntegrationSettings(payload);
      setSlackWebhook("");
      await reloadIntegrations();
      setIntegrationMsg("Slack settings saved.");
    } catch (err) {
      setIntegrationMsg(err.message || "Failed to save Slack settings");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleTestSlack() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const res = await testSlackIntegration(
        slackWebhook.trim() ? { webhook_url: slackWebhook.trim() } : {}
      );
      setIntegrationMsg(res?.detail || "Slack test sent.");
      await reloadIntegrations();
    } catch (err) {
      setIntegrationMsg(err.message || "Slack test failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleClearSlackWebhook() {
    setIntegrationBusy(true);
    try {
      await updateIntegrationSettings({ slack: { clear_webhook: true } });
      await reloadIntegrations();
      setIntegrationMsg("Slack webhook cleared.");
    } catch (err) {
      setIntegrationMsg(err.message || "Clear failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleSaveGithub(e) {
    e.preventDefault();
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const payload = {
        github: {
          owner: githubOwner.trim(),
          repo: githubRepo.trim(),
        },
      };
      if (githubToken.trim()) payload.github.token = githubToken.trim();
      await updateIntegrationSettings(payload);
      setGithubToken("");
      await reloadIntegrations();
      setIntegrationMsg("GitHub settings saved.");
    } catch (err) {
      setIntegrationMsg(err.message || "Failed to save GitHub settings");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleVerifyGithub() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const res = await verifyGithub();
      setIntegrationMsg(res?.detail || "GitHub verified.");
      await reloadIntegrations();
    } catch (err) {
      setIntegrationMsg(err.message || "GitHub verification failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleClearGithubToken() {
    setIntegrationBusy(true);
    try {
      await updateIntegrationSettings({ github: { clear_token: true } });
      await reloadIntegrations();
      setIntegrationMsg("GitHub token cleared.");
    } catch (err) {
      setIntegrationMsg(err.message || "Clear failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleSaveDiscord(e) {
    e.preventDefault();
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const payload = { discord: { default_channel: discordChannel.trim() } };
      if (discordWebhook.trim()) payload.discord.webhook_url = discordWebhook.trim();
      await updateIntegrationSettings(payload);
      setDiscordWebhook("");
      await reloadIntegrations();
      setIntegrationMsg("Discord settings saved.");
    } catch (err) {
      setIntegrationMsg(err.message || "Failed to save Discord");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleTestDiscord() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const res = await testDiscordIntegration(
        discordWebhook.trim() ? { webhook_url: discordWebhook.trim() } : {}
      );
      setIntegrationMsg(res?.detail || "Discord test sent.");
      await reloadIntegrations();
    } catch (err) {
      setIntegrationMsg(err.message || "Discord test failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleClearDiscordWebhook() {
    setIntegrationBusy(true);
    try {
      await updateIntegrationSettings({ discord: { clear_webhook: true } });
      await reloadIntegrations();
      setIntegrationMsg("Discord webhook cleared.");
    } catch (err) {
      setIntegrationMsg(err.message || "Clear failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleSaveLinear(e) {
    e.preventDefault();
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const payload = { linear: { team_id: linearTeamId.trim() } };
      if (linearApiKey.trim()) payload.linear.api_key = linearApiKey.trim();
      await updateIntegrationSettings(payload);
      setLinearApiKey("");
      await reloadIntegrations();
      setIntegrationMsg("Linear settings saved.");
    } catch (err) {
      setIntegrationMsg(err.message || "Failed to save Linear");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleVerifyLinear() {
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const res = await verifyLinear();
      setIntegrationMsg(res?.detail || "Linear verified.");
      await reloadIntegrations();
    } catch (err) {
      setIntegrationMsg(err.message || "Linear verification failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleClearLinearKey() {
    setIntegrationBusy(true);
    try {
      await updateIntegrationSettings({ linear: { clear_api_key: true } });
      await reloadIntegrations();
      setIntegrationMsg("Linear API key cleared.");
    } catch (err) {
      setIntegrationMsg(err.message || "Clear failed");
    } finally {
      setIntegrationBusy(false);
    }
  }

  async function handleSaveSlackBot(e) {
    e.preventDefault();
    setIntegrationBusy(true);
    setIntegrationMsg("");
    try {
      const payload = { slack: {} };
      if (slackBotToken.trim()) payload.slack.bot_token = slackBotToken.trim();
      if (slackSigningSecret.trim()) payload.slack.signing_secret = slackSigningSecret.trim();
      await updateIntegrationSettings(payload);
      setSlackBotToken("");
      setSlackSigningSecret("");
      await reloadIntegrations();
      setIntegrationMsg("Slack bot credentials saved.");
    } catch (err) {
      setIntegrationMsg(err.message || "Failed to save Slack bot");
    } finally {
      setIntegrationBusy(false);
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

  async function handleVerifyProvider(id) {
    setProviderBusy(id);
    setProviderMsg("");
    try {
      const res = await verifyLlmProvider(id);
      const emb =
        res?.embedding_ok === true
          ? " · embeddings OK"
          : res?.embedding_ok === false
            ? " · embeddings failed"
            : "";
      setProviderMsg(`Provider test passed (${res?.model || "model"})${emb}.`);
    } catch (err) {
      setProviderMsg(err.message || "Provider test failed");
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
      setPwdMsg("Password updated. Sign in again with your new password.");
      try {
        const { logout } = await import("@/lib/api/auth");
        await logout();
      } catch (_) {}
      setTimeout(() => {
        window.location.href = "/login";
      }, 1200);
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
    return <WorkspacePageShell loading loadingMessage="Loading settings…" />;
  }

  return (
    <WorkspacePageShell user={user}>
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
                onClick={() => {
                  load();
                  if (canManageWorkspace || isPlatformAdmin || canManageApiKeys) {
                    reloadAdminSections();
                  }
                }}
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
                hint={canManageWorkspace ? `Workspace ${workspaceRole}` : user.role || workspaceRole || "Member"}
              />
              {canManageWorkspace ? (
                <SettingsStatCard
                  label="Integrations"
                  value={
                    integrationHealth?.telegram_ready && integrationHealth?.email_ready
                      ? "Ready"
                      : integrationHealth?.telegram_ready || integrationHealth?.email_ready
                        ? "Partial"
                        : "Setup"
                  }
                  hint={`TG: ${integrationHealth?.telegram_ready ? "on" : "off"} · Email: ${integrationHealth?.email_ready ? "on" : "off"}`}
                  status={
                    integrationHealth?.telegram_ready || integrationHealth?.email_ready ? "online" : undefined
                  }
                />
              ) : (
                <SettingsStatCard label="Role" value={user.role || "Member"} hint="Contact admin for elevated access" />
              )}
            </div>
          </WorkspaceHero>

          {readOnly ? (
            <WorkspaceAlert type="warn" className="mt-4">
              View-only access — you cannot change workspace settings.
            </WorkspaceAlert>
          ) : null}

          {loadError ? (
            <WorkspaceAlert type="error" className="mt-4">
              {loadError}
              <button
                type="button"
                onClick={() => load()}
                className="ml-2 rounded-full border border-red-200 bg-white px-3 py-0.5 text-xs font-medium text-red-700 hover:bg-red-50"
              >
                Retry
              </button>
            </WorkspaceAlert>
          ) : null}

          {adminLoadError ? (
            <WorkspaceAlert type="error" className="mt-4">
              {adminLoadError}
              <button
                type="button"
                onClick={() => reloadAdminSections()}
                className="ml-2 rounded-full border border-red-200 bg-white px-3 py-0.5 text-xs font-medium text-red-700 hover:bg-red-50"
              >
                Retry
              </button>
            </WorkspaceAlert>
          ) : null}

          <div className="settings-layout mt-8 lg:mt-10">
            <aside className="settings-sidebar shrink-0">
              <SettingsNav activeTab={activeTab} onChange={setActiveTab} canManageWorkspace={canManageWorkspace} />
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
                        : loadError
                          ? "Could not load model providers"
                          : `${llmServers.length} provider${llmServers.length !== 1 ? "s" : ""}, ${modelCount} model${modelCount !== 1 ? "s" : ""}`}
                    </p>
                    {modelLoadWarning ? (
                      <SettingsMessage type="error">{modelLoadWarning}</SettingsMessage>
                    ) : null}
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
                    {canEditWorkspace && (
                      <button
                        type="button"
                        onClick={() => router.push("/credentials")}
                        className="workspace-btn-ghost mt-5 !py-2 text-sm"
                      >
                        Manage credentials & integrations →
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
                      <Link href="/projects?tab=assistants" className="workspace-btn-ghost">Projects</Link>
                      <Link href="/knowledge" className="workspace-btn-ghost">Knowledge</Link>
                      <Link href="/workflows" className="workspace-btn-ghost">Workflows</Link>
                      <Link href="/chat" className="workspace-btn-ghost">Chat</Link>
                      {(isPlatformAdmin || canManageApiKeys) && (
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

                  {isPlatformAdmin && (
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

              {activeTab === "models" && isPlatformAdmin && (
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
                                <button
                                  type="button"
                                  disabled={providerBusy === p.id}
                                  onClick={() => handleVerifyProvider(p.id)}
                                  className="workspace-btn-ghost !px-2.5 !py-1.5 text-xs"
                                >
                                  Test
                                </button>
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

              {activeTab === "integrations" && canManageWorkspace && (
                <>
                  <SettingsSection
                    icon={SECTION_ICONS.health}
                    title="Integration status"
                    description="Live readiness for Telegram, email, Slack, Jira, and GitHub."
                    delay={0.01}
                  >
                    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                      <div className="rounded-xl border border-black/[0.06] bg-white/70 p-4">
                        <p className="text-xs font-semibold text-neutral-500">Telegram</p>
                        <p className="mt-1 text-sm font-semibold">
                          {integrationHealth?.telegram_ready ? "Ready" : "Not configured"}
                        </p>
                        <p className="text-xs text-neutral-400">Source: {integrationSettings?.telegram?.source || "—"}</p>
                      </div>
                      <div className="rounded-xl border border-black/[0.06] bg-white/70 p-4">
                        <p className="text-xs font-semibold text-neutral-500">Email / Gmail</p>
                        <p className="mt-1 text-sm font-semibold">
                          {integrationHealth?.email_ready ? "Ready" : "Not configured"}
                        </p>
                        <p className="text-xs text-neutral-400">
                          Source: {integrationSettings?.email?.source || "—"}
                          {integrationSettings?.email?.oauth_connected
                            ? ` · ${integrationSettings.email.oauth_email || "OAuth"}`
                            : ""}
                        </p>
                      </div>
                      <div className="rounded-xl border border-black/[0.06] bg-white/70 p-4">
                        <p className="text-xs font-semibold text-neutral-500">Slack</p>
                        <p className="mt-1 text-sm font-semibold">
                          {integrationHealth?.slack_ready ? "Ready" : "Not configured"}
                        </p>
                        <p className="text-xs text-neutral-400">Source: {integrationSettings?.slack?.source || "—"}</p>
                      </div>
                      <div className="rounded-xl border border-black/[0.06] bg-white/70 p-4">
                        <p className="text-xs font-semibold text-neutral-500">Jira</p>
                        <p className="mt-1 text-sm font-semibold">
                          {integrationHealth?.jira_ready ? "Ready" : "Not configured"}
                        </p>
                        <p className="text-xs text-neutral-400">Source: {integrationSettings?.jira?.source || "—"}</p>
                      </div>
                      <div className="rounded-xl border border-black/[0.06] bg-white/70 p-4">
                        <p className="text-xs font-semibold text-neutral-500">GitHub</p>
                        <p className="mt-1 text-sm font-semibold">
                          {integrationHealth?.github_ready ? "Ready" : "Not configured"}
                        </p>
                        <p className="text-xs text-neutral-400">Source: {integrationSettings?.github?.source || "—"}</p>
                      </div>
                    </div>
                    <label className="mt-4 block">
                      <span className="text-xs font-semibold text-neutral-600">Public API base URL</span>
                      <input
                        value={publicBaseUrl}
                        onChange={(e) => setPublicBaseUrl(e.target.value)}
                        placeholder="https://api.yourdomain.com"
                        className="input-field mt-2 w-full font-mono text-sm"
                      />
                      <span className="mt-1 block text-xs text-neutral-500">
                        Used for Telegram webhook registration in production
                      </span>
                    </label>
                    <button
                      type="button"
                      disabled={integrationBusy}
                      onClick={handleSaveIntegrations}
                      className="btn-secondary mt-3 text-xs"
                    >
                      Save public URL
                    </button>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.telegram}
                    title="Telegram bot"
                    description={
                      <>
                        Add your bot token from{" "}
                        <a
                          href="https://t.me/BotFather"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-neutral-800 underline-offset-2 hover:underline"
                        >
                          @BotFather
                        </a>
                        . Used by workflow notify nodes and project bots. Stored encrypted per workspace.
                      </>
                    }
                    delay={0.02}
                  >
                    <SettingsMessage
                      type={
                        integrationMsg.includes("saved") ||
                        integrationMsg.includes("sent") ||
                        integrationMsg.includes("Connected")
                          ? "success"
                          : integrationMsg
                            ? "error"
                            : "info"
                      }
                    >
                      {integrationMsg ||
                        (integrationSettings?.telegram?.configured
                          ? `Bot configured (${integrationSettings.telegram.source})${integrationSettings.telegram.bot_token_masked ? ` · ${integrationSettings.telegram.bot_token_masked}` : ""}`
                          : "No Telegram bot configured yet.")}
                    </SettingsMessage>

                    <form onSubmit={handleSaveIntegrations} className="mt-5 space-y-4">
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Bot token</span>
                        <input
                          type="password"
                          value={tgToken}
                          onChange={(e) => setTgToken(e.target.value)}
                          placeholder={
                            integrationSettings?.telegram?.bot_token_masked
                              ? `Saved ${integrationSettings.telegram.bot_token_masked} — enter to replace`
                              : "123456:ABC-DEF..."
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <label className="block">
                          <span className="text-xs font-semibold text-neutral-600">Bot username</span>
                          <input
                            value={tgUsername}
                            onChange={(e) => setTgUsername(e.target.value)}
                            placeholder="@myprojectbot"
                            className="input-field mt-2 w-full text-sm"
                          />
                        </label>
                        <label className="block">
                          <span className="text-xs font-semibold text-neutral-600">Default chat ID</span>
                          <input
                            value={tgChatId}
                            onChange={(e) => setTgChatId(e.target.value)}
                            placeholder="-1001234567890"
                            className="input-field mt-2 w-full font-mono text-sm"
                          />
                        </label>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button type="submit" disabled={integrationBusy} className="btn-primary disabled:opacity-50">
                          {integrationBusy ? "Saving…" : "Save Telegram"}
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleVerifyTelegram}
                          className="btn-secondary disabled:opacity-50"
                        >
                          Verify bot
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy || !tgChatId.trim()}
                          onClick={handleTestTelegram}
                          className="workspace-btn-ghost disabled:opacity-50"
                        >
                          Send test
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleClearTelegramToken}
                          className="workspace-btn-ghost workspace-btn-danger text-xs"
                        >
                          Clear token
                        </button>
                      </div>
                    </form>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.email}
                    title="Gmail & email"
                    description="Connect Gmail with Google OAuth, or use an app password / any SMTP server for digests, alerts, and notify nodes."
                    delay={0.04}
                  >
                    <div className="rounded-xl border border-black/[0.06] bg-white/80 p-4">
                      <p className="text-sm font-semibold">Google OAuth (recommended)</p>
                      <p className="mt-1 text-xs text-neutral-500">
                        {integrationSettings?.email?.oauth_enabled
                          ? "Add both redirect URIs below in Google Cloud Console, then connect."
                          : "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET on the backend to enable Connect with Google."}
                      </p>
                      {oauthSetup?.google?.redirect_uris?.length ? (
                        <div className="mt-3 space-y-2 rounded-lg bg-neutral-50 p-3 text-xs text-neutral-700">
                          <p className="font-semibold text-neutral-800">Authorized redirect URIs (Google Console)</p>
                          {oauthSetup.google.redirect_uris.map((row) => (
                            <div key={row.id}>
                              <p className="font-medium text-neutral-600">{row.label}</p>
                              <p className="break-all font-mono text-[11px]">{row.uri}</p>
                            </div>
                          ))}
                        </div>
                      ) : null}
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={integrationBusy || !integrationSettings?.email?.oauth_enabled}
                          onClick={handleConnectGmailOAuth}
                          className="btn-primary disabled:opacity-50"
                        >
                          {integrationSettings?.email?.oauth_connected ? "Reconnect Google" : "Connect with Google"}
                        </button>
                        {integrationSettings?.email?.oauth_connected && (
                          <button
                            type="button"
                            disabled={integrationBusy}
                            onClick={handleDisconnectGmailOAuth}
                            className="workspace-btn-ghost workspace-btn-danger text-xs"
                          >
                            Disconnect OAuth
                          </button>
                        )}
                      </div>
                      {integrationSettings?.email?.oauth_connected && (
                        <p className="mt-2 text-xs text-emerald-700">
                          Connected as {integrationSettings.email.oauth_email || "Gmail account"}
                        </p>
                      )}
                    </div>

                    <p className="mt-5 text-xs font-semibold uppercase tracking-wide text-neutral-400">
                      Or use SMTP / app password
                    </p>

                    <label className="mt-3 flex items-center gap-2 text-sm text-neutral-700">
                      <input
                        type="checkbox"
                        checked={gmailPreset}
                        onChange={(e) => {
                          setGmailPreset(e.target.checked);
                          if (e.target.checked) {
                            setSmtpHost("smtp.gmail.com");
                            setSmtpPort(587);
                          }
                        }}
                      />
                      Gmail preset (smtp.gmail.com:587)
                    </label>

                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      {!gmailPreset && (
                        <>
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-600">SMTP host</span>
                            <input
                              value={smtpHost}
                              onChange={(e) => setSmtpHost(e.target.value)}
                              className="input-field mt-2 w-full text-sm"
                            />
                          </label>
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-600">SMTP port</span>
                            <input
                              type="number"
                              value={smtpPort}
                              onChange={(e) => setSmtpPort(e.target.value)}
                              className="input-field mt-2 w-full text-sm"
                            />
                          </label>
                        </>
                      )}
                      <label className="block sm:col-span-2">
                        <span className="text-xs font-semibold text-neutral-600">Email / username</span>
                        <input
                          value={smtpUser}
                          onChange={(e) => setSmtpUser(e.target.value)}
                          placeholder="you@gmail.com"
                          className="input-field mt-2 w-full text-sm"
                        />
                      </label>
                      <label className="block sm:col-span-2">
                        <span className="text-xs font-semibold text-neutral-600">From address</span>
                        <input
                          value={smtpFrom}
                          onChange={(e) => setSmtpFrom(e.target.value)}
                          placeholder="Optional — defaults to username"
                          className="input-field mt-2 w-full text-sm"
                        />
                      </label>
                      <label className="block sm:col-span-2">
                        <span className="text-xs font-semibold text-neutral-600">App password / SMTP password</span>
                        <input
                          type="password"
                          value={smtpPassword}
                          onChange={(e) => setSmtpPassword(e.target.value)}
                          placeholder={
                            integrationSettings?.email?.smtp_password_masked
                              ? `Saved ${integrationSettings.email.smtp_password_masked} — enter to replace`
                              : "Gmail app password"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={integrationBusy}
                        onClick={handleSaveIntegrations}
                        className="btn-primary disabled:opacity-50"
                      >
                        Save email settings
                      </button>
                      <button
                        type="button"
                        disabled={integrationBusy}
                        onClick={handleTestEmail}
                        className="btn-secondary disabled:opacity-50"
                      >
                        Send test email
                      </button>
                      <button
                        type="button"
                        disabled={integrationBusy}
                        onClick={handleClearSmtpPassword}
                        className="workspace-btn-ghost workspace-btn-danger text-xs"
                      >
                        Clear password
                      </button>
                    </div>
                    <p className="mt-3 text-xs text-neutral-500">
                      Status:{" "}
                      {integrationSettings?.email?.configured
                        ? `Configured (${integrationSettings.email.source}${
                            integrationSettings.email.auth_mode === "oauth" ? " · OAuth" : " · SMTP"
                          })`
                        : "Not configured"}
                    </p>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.keys}
                    title="Jira Cloud"
                    description="Store Atlassian site URL, account email, and API token for the Jira workflow node."
                    delay={0.045}
                  >
                    <form onSubmit={handleSaveJira} className="space-y-4">
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Site URL</span>
                        <input
                          value={jiraBaseUrl}
                          onChange={(e) => setJiraBaseUrl(e.target.value)}
                          placeholder="https://your-domain.atlassian.net"
                          className="input-field mt-2 w-full text-sm"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Atlassian email</span>
                        <input
                          value={jiraEmail}
                          onChange={(e) => setJiraEmail(e.target.value)}
                          placeholder="you@company.com"
                          className="input-field mt-2 w-full text-sm"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">API token</span>
                        <input
                          type="password"
                          value={jiraApiToken}
                          onChange={(e) => setJiraApiToken(e.target.value)}
                          placeholder={
                            integrationSettings?.jira?.api_token_masked
                              ? `Saved ${integrationSettings.jira.api_token_masked} — enter to replace`
                              : "Atlassian API token"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button type="submit" disabled={integrationBusy} className="btn-primary disabled:opacity-50">
                          Save Jira
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleVerifyJira}
                          className="btn-secondary disabled:opacity-50"
                        >
                          Verify
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleClearJiraToken}
                          className="workspace-btn-ghost workspace-btn-danger text-xs"
                        >
                          Clear token
                        </button>
                      </div>
                    </form>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.telegram}
                    title="Slack"
                    description="Incoming webhook for notify nodes and digests. Create one in Slack → Apps → Incoming Webhooks."
                    delay={0.046}
                  >
                    <form onSubmit={handleSaveSlack} className="space-y-4">
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Webhook URL</span>
                        <input
                          type="password"
                          value={slackWebhook}
                          onChange={(e) => setSlackWebhook(e.target.value)}
                          placeholder={
                            integrationSettings?.slack?.webhook_url_masked
                              ? `Saved ${integrationSettings.slack.webhook_url_masked} — enter to replace`
                              : "https://hooks.slack.com/services/…"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Default channel (label)</span>
                        <input
                          value={slackChannel}
                          onChange={(e) => setSlackChannel(e.target.value)}
                          placeholder="#ops-alerts"
                          className="input-field mt-2 w-full text-sm"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button type="submit" disabled={integrationBusy} className="btn-primary disabled:opacity-50">
                          Save Slack
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleTestSlack}
                          className="btn-secondary disabled:opacity-50"
                        >
                          Send test
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleClearSlackWebhook}
                          className="workspace-btn-ghost workspace-btn-danger text-xs"
                        >
                          Clear webhook
                        </button>
                      </div>
                    </form>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.keys}
                    title="GitHub Issues"
                    description="Personal access token with repo issues scope for the GitHub workflow node."
                    delay={0.047}
                  >
                    <form onSubmit={handleSaveGithub} className="space-y-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <label className="block">
                          <span className="text-xs font-semibold text-neutral-600">Default owner</span>
                          <input
                            value={githubOwner}
                            onChange={(e) => setGithubOwner(e.target.value)}
                            placeholder="acme-org"
                            className="input-field mt-2 w-full text-sm"
                          />
                        </label>
                        <label className="block">
                          <span className="text-xs font-semibold text-neutral-600">Default repo</span>
                          <input
                            value={githubRepo}
                            onChange={(e) => setGithubRepo(e.target.value)}
                            placeholder="novaflow"
                            className="input-field mt-2 w-full text-sm"
                          />
                        </label>
                      </div>
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Personal access token</span>
                        <input
                          type="password"
                          value={githubToken}
                          onChange={(e) => setGithubToken(e.target.value)}
                          placeholder={
                            integrationSettings?.github?.token_masked
                              ? `Saved ${integrationSettings.github.token_masked} — enter to replace`
                              : "ghp_…"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button type="submit" disabled={integrationBusy} className="btn-primary disabled:opacity-50">
                          Save GitHub
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleVerifyGithub}
                          className="btn-secondary disabled:opacity-50"
                        >
                          Verify
                        </button>
                        <button
                          type="button"
                          disabled={integrationBusy}
                          onClick={handleClearGithubToken}
                          className="workspace-btn-ghost workspace-btn-danger text-xs"
                        >
                          Clear token
                        </button>
                      </div>
                    </form>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.telegram}
                    title="Discord"
                    description="Incoming webhook for notify nodes and digests."
                    delay={0.048}
                  >
                    <form onSubmit={handleSaveDiscord} className="space-y-4">
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Webhook URL</span>
                        <input
                          type="password"
                          value={discordWebhook}
                          onChange={(e) => setDiscordWebhook(e.target.value)}
                          placeholder={
                            integrationSettings?.discord?.webhook_url_masked
                              ? `Saved ${integrationSettings.discord.webhook_url_masked} — enter to replace`
                              : "https://discord.com/api/webhooks/…"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Channel label</span>
                        <input
                          value={discordChannel}
                          onChange={(e) => setDiscordChannel(e.target.value)}
                          placeholder="#alerts"
                          className="input-field mt-2 w-full text-sm"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button type="submit" disabled={integrationBusy} className="btn-primary disabled:opacity-50">
                          Save Discord
                        </button>
                        <button type="button" disabled={integrationBusy} onClick={handleTestDiscord} className="btn-secondary disabled:opacity-50">
                          Send test
                        </button>
                        <button type="button" disabled={integrationBusy} onClick={handleClearDiscordWebhook} className="workspace-btn-ghost workspace-btn-danger text-xs">
                          Clear webhook
                        </button>
                      </div>
                    </form>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.keys}
                    title="Linear"
                    description="API key + default team ID for the Linear workflow node."
                    delay={0.049}
                  >
                    <form onSubmit={handleSaveLinear} className="space-y-4">
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Default team ID</span>
                        <input
                          value={linearTeamId}
                          onChange={(e) => setLinearTeamId(e.target.value)}
                          placeholder="Linear team UUID"
                          className="input-field mt-2 w-full font-mono text-sm"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">API key</span>
                        <input
                          type="password"
                          value={linearApiKey}
                          onChange={(e) => setLinearApiKey(e.target.value)}
                          placeholder={
                            integrationSettings?.linear?.api_key_masked
                              ? `Saved ${integrationSettings.linear.api_key_masked} — enter to replace`
                              : "lin_api_…"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button type="submit" disabled={integrationBusy} className="btn-primary disabled:opacity-50">
                          Save Linear
                        </button>
                        <button type="button" disabled={integrationBusy} onClick={handleVerifyLinear} className="btn-secondary disabled:opacity-50">
                          Verify
                        </button>
                        <button type="button" disabled={integrationBusy} onClick={handleClearLinearKey} className="workspace-btn-ghost workspace-btn-danger text-xs">
                          Clear key
                        </button>
                      </div>
                    </form>
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.telegram}
                    title="Slack Bot (Events API)"
                    description="Bot token + signing secret for inbound Slack → workflow. Bind a workflow in the builder inspector."
                    delay={0.05}
                  >
                    <form onSubmit={handleSaveSlackBot} className="space-y-4">
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Bot user OAuth token</span>
                        <input
                          type="password"
                          value={slackBotToken}
                          onChange={(e) => setSlackBotToken(e.target.value)}
                          placeholder={
                            integrationSettings?.slack?.bot_token_masked
                              ? `Saved ${integrationSettings.slack.bot_token_masked} — enter to replace`
                              : "xoxb-…"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold text-neutral-600">Signing secret</span>
                        <input
                          type="password"
                          value={slackSigningSecret}
                          onChange={(e) => setSlackSigningSecret(e.target.value)}
                          placeholder={
                            integrationSettings?.slack?.signing_secret_masked
                              ? `Saved ${integrationSettings.slack.signing_secret_masked} — enter to replace`
                              : "Slack app signing secret"
                          }
                          className="input-field mt-2 w-full font-mono text-sm"
                          autoComplete="off"
                        />
                      </label>
                      <p className="text-xs text-neutral-500">
                        Status: {integrationSettings?.slack?.bot_configured ? "Bot ready" : "Not configured"}
                        {integrationSettings?.slack?.events_url
                          ? ` · bound ${integrationSettings.slack.events_url}`
                          : ""}
                      </p>
                      <button type="submit" disabled={integrationBusy} className="btn-primary disabled:opacity-50">
                        Save Slack bot
                      </button>
                    </form>
                  </SettingsSection>

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

              {activeTab === "team" && canManageWorkspace && (
                <>
                  {teamMsg ? (
                    <SettingsMessage
                      type={teamMsg.includes("updated") || teamMsg.includes("revoked") ? "success" : "error"}
                    >
                      {teamMsg}
                    </SettingsMessage>
                  ) : null}
                  <SettingsSection
                    icon={SECTION_ICONS.team}
                    title="Invite members"
                    description="Send an email invite to join the active workspace."
                    delay={0.05}
                  >
                    <form onSubmit={handleInvite} className="flex flex-col gap-3 sm:flex-row sm:items-end">
                      <label className="min-w-0 flex-1 space-y-1">
                        <span className="text-xs font-semibold text-neutral-600">Email</span>
                        <input
                          type="email"
                          required
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                          placeholder="colleague@company.com"
                          disabled={readOnly}
                          className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm disabled:opacity-60"
                        />
                      </label>
                      <label className="space-y-1 sm:w-36">
                        <span className="text-xs font-semibold text-neutral-600">Role</span>
                        <select
                          value={inviteRole}
                          onChange={(e) => setInviteRole(e.target.value)}
                          disabled={readOnly}
                          className="settings-role-select w-full rounded-lg border border-black/10 bg-white px-2.5 py-2 text-xs font-semibold disabled:opacity-60"
                        >
                          <option value="admin">Admin</option>
                          <option value="manager">Manager</option>
                          <option value="developer">Developer</option>
                          <option value="editor">Editor</option>
                          <option value="analyst">Analyst</option>
                          <option value="viewer">Viewer</option>
                          <option value="guest">Guest</option>
                        </select>
                      </label>
                      <button
                        type="submit"
                        disabled={readOnly}
                        className="rounded-lg bg-foreground px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
                      >
                        Send invite
                      </button>
                    </form>
                    {inviteMsg ? (
                      <SettingsMessage type={inviteMsg.includes("sent") ? "success" : "error"}>
                        {inviteMsg}
                      </SettingsMessage>
                    ) : null}
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.team}
                    title="Team & roles"
                    description="Manage workspace access for your team."
                    delay={0.08}
                  >
                    {teamLoadError ? (
                      <SettingsMessage type="error">
                        {teamLoadError}
                        <button
                          type="button"
                          onClick={() => reloadWorkspaceTeam()}
                          className="ml-2 rounded-full border border-red-200 bg-white px-2 py-0.5 text-xs font-medium text-red-700"
                        >
                          Retry
                        </button>
                      </SettingsMessage>
                    ) : team.length === 0 ? (
                      <SettingsEmpty>No team members found.</SettingsEmpty>
                    ) : (
                      <ul className="space-y-2">
                        {team.map((member) => (
                          <SettingsListItem key={member.user_id}>
                            <div>
                              <p className="text-sm font-medium">{member.user_name}</p>
                              <p className="text-[11px] text-neutral-400">
                                {member.email || `ID ${member.user_id}`}
                              </p>
                            </div>
                            <select
                              value={member.role || "editor"}
                              disabled={readOnly || teamBusy === member.user_id || member.role === "owner"}
                              onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                              className="settings-role-select rounded-lg border border-black/10 bg-white px-2.5 py-1.5 text-xs font-semibold disabled:opacity-60"
                            >
                              <option value="owner">Owner</option>
                              <option value="admin">Admin</option>
                              <option value="manager">Manager</option>
                              <option value="developer">Developer</option>
                              <option value="editor">Editor</option>
                              <option value="analyst">Analyst</option>
                              <option value="viewer">Viewer</option>
                              <option value="guest">Guest</option>
                            </select>
                          </SettingsListItem>
                        ))}
                      </ul>
                    )}
                  </SettingsSection>

                  <SettingsSection
                    icon={SECTION_ICONS.team}
                    title="Pending invites"
                    description="Invitations waiting to be accepted."
                    delay={0.11}
                  >
                    {invites.filter((i) => i.status === "pending").length === 0 ? (
                      <SettingsEmpty>No pending invitations.</SettingsEmpty>
                    ) : (
                      <ul className="space-y-2">
                        {invites
                          .filter((i) => i.status === "pending")
                          .map((inv) => (
                            <SettingsListItem key={inv.id}>
                              <div>
                                <p className="text-sm font-medium">{inv.email}</p>
                                <p className="text-[11px] text-neutral-400">
                                  {inv.role} · expires {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : "—"}
                                </p>
                              </div>
                              <button
                                type="button"
                                disabled={readOnly || teamBusy === inv.id}
                                onClick={() => handleRevokeInvite(inv.id)}
                                className="rounded-lg border border-black/10 px-2.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-50 disabled:opacity-50"
                              >
                                Revoke
                              </button>
                            </SettingsListItem>
                          ))}
                      </ul>
                    )}
                  </SettingsSection>
                </>
              )}
            </div>
          </div>
    </WorkspacePageShell>
  );
}
