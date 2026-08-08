"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import CopyUriBox from "@/components/workspace/CopyUriBox";
import WorkspaceEmpty from "@/components/workspace/WorkspaceEmpty";
import { WorkspaceSkeletonList, WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { useWorkspaceAccess } from "@/lib/auth/workspaceAccess";
import { getUserInfo } from "@/lib/api/auth";
import { ensureActiveWorkspace, workspaceCanManageApiKeys } from "@/lib/api/workspaces";
import {
  createCredential,
  deleteCredential,
  getCredentialsCatalog,
  getCredentialsOverview,
  getOAuthSetup,
  listCredentials,
  setDefaultCredential,
  updateCredential,
  verifyCredential,
} from "@/lib/api/credentials";
import { startGmailOAuth } from "@/lib/api/integrations";
import { humanizeCredentialError } from "@/lib/humanizeErrors";
import {
  createApiKey,
  deleteApiKey,
  listApiKeys,
} from "@/lib/api/apiKeys";

const CATEGORY_TABS = [
  { id: "overview", label: "Overview" },
  { id: "llm", label: "AI / Models" },
  { id: "email", label: "Email & Gmail" },
  { id: "messaging", label: "Messaging" },
  { id: "devtools", label: "Dev tools" },
  { id: "api_keys", label: "Platform keys" },
  { id: "digests", label: "Digests" },
];

const OAUTH_FORM_HINTS = {
  "email::gmail_oauth":
    "Connect Gmail in Settings → Integrations, or paste OAuth refresh tokens from Google.",
  "outlook::microsoft_graph":
    "Register an Azure app and paste tokens, or complete setup in Settings → Integrations.",
};

const DEV_CATS = new Set(["github", "jira", "linear", "webhook", "custom"]);
const MESSAGING_CATS = new Set(["telegram", "slack", "discord", "whatsapp"]);

const PLACEHOLDER_EMAILS = new Set(["you@gmail.com", "user@example.com", "test@example.com", "me@gmail.com"]);

function isPlaceholderField(category, key, value) {
  const val = (value || "").trim();
  if (!val || val.length < 4) return true;
  const low = val.toLowerCase();
  if (low.startsWith("paste:")) return true;
  if ((key === "smtp_user" || key === "smtp_from" || key === "email") && PLACEHOLDER_EMAILS.has(low)) return true;
  if (low.includes("@example.")) return true;
  if (key === "smtp_password" && /^x{4}(\s+x{4}){3}$/i.test(low)) return true;
  return false;
}

function isPermissionError(err) {
  const msg = String(err?.message || "").toLowerCase();
  return msg.includes("403") || msg.includes("forbidden") || msg.includes("permission");
}

function OAuthSetupPanel({ setup, onConnectGmail }) {
  const google = setup?.google;
  if (!google) return null;
  return (
    <div className="space-y-3 rounded-xl border border-sky-200 bg-sky-50/80 p-4 text-sm text-sky-950">
      <p className="font-semibold">Google Cloud Console setup</p>
      <p className="text-xs text-sky-800">{google.instructions}</p>
      <a href={google.console_url} target="_blank" rel="noreferrer" className="text-xs font-semibold underline">
        Open Google Cloud Credentials
      </a>
      <div className="space-y-3">
        {(google.redirect_uris || []).map((row) => (
          <CopyUriBox key={row.id} label={row.label} uri={row.uri} />
        ))}
      </div>
      {onConnectGmail ? (
        <button type="button" className="btn-primary !py-2 !text-sm" onClick={onConnectGmail}>
          Connect with Google (Gmail send)
        </button>
      ) : null}
    </div>
  );
}

function emptyFields(spec) {
  const out = {};
  (spec?.fields || []).forEach((f) => {
    out[f.key] = "";
  });
  (spec?.advanced_fields || []).forEach((f) => {
    out[f.key] = "";
  });
  return out;
}

export default function CredentialsClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { role: workspaceRole, readOnly: workspaceReadOnly } = useWorkspaceAccess();
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState("overview");
  const [catalog, setCatalog] = useState([]);
  const [entries, setEntries] = useState([]);
  const [overview, setOverview] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formKind, setFormKind] = useState("");
  const [formLabel, setFormLabel] = useState("default");
  const [formFields, setFormFields] = useState({});
  const [formDefault, setFormDefault] = useState(true);
  const [newKeyName, setNewKeyName] = useState("API key");
  const [createdRawKey, setCreatedRawKey] = useState("");
  const [oauthSetup, setOauthSetup] = useState(null);
  const [showAdvancedOAuth, setShowAdvancedOAuth] = useState(false);
  const [formErrors, setFormErrors] = useState([]);

  useEffect(() => {
    const q = (searchParams?.get("tab") || "").trim();
    if (q && ["overview", "api_keys", "digests", "llm", "email", "messaging", "devtools"].includes(q)) {
      setTab(q);
    }
  }, [searchParams]);

  const readOnly = workspaceReadOnly || user?.role === "viewer";
  const canManageApiKeys = workspaceCanManageApiKeys(workspaceRole);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    setLoadError("");
    try {
      const [cat, list, ov, oauth] = await Promise.all([
        getCredentialsCatalog(),
        listCredentials(),
        getCredentialsOverview(),
        getOAuthSetup(),
      ]);
      setCatalog(Array.isArray(cat) ? cat : []);
      setEntries(Array.isArray(list) ? list : []);
      setOverview(ov || null);
      setOauthSetup(oauth || null);

      if (canManageApiKeys) {
        try {
          const keys = await listApiKeys();
          setApiKeys(Array.isArray(keys) ? keys : []);
        } catch (apiErr) {
          if (isPermissionError(apiErr)) {
            setApiKeys([]);
          } else {
            throw apiErr;
          }
        }
      } else {
        setApiKeys([]);
      }
    } catch (e) {
      setLoadError(e.message || "Failed to load credentials");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [canManageApiKeys]);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        try {
          await ensureActiveWorkspace();
        } catch {
          /* workspace bootstrap optional */
        }
        setUser(u);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const filtered = useMemo(() => {
    if (tab === "overview" || tab === "api_keys" || tab === "digests") return entries;
    if (tab === "llm") return entries.filter((e) => e.category === "llm");
    if (tab === "email") return entries.filter((e) => e.category === "email" || e.category === "google");
    if (tab === "messaging") return entries.filter((e) => MESSAGING_CATS.has(e.category));
    if (tab === "devtools") return entries.filter((e) => DEV_CATS.has(e.category));
    return entries;
  }, [entries, tab]);

  const kindOptions = useMemo(() => {
    if (tab === "llm") return catalog.filter((c) => c.category === "llm");
    if (tab === "email") return catalog.filter((c) => c.category === "email" || c.category === "google");
    if (tab === "messaging") return catalog.filter((c) => MESSAGING_CATS.has(c.category));
    if (tab === "devtools") return catalog.filter((c) => DEV_CATS.has(c.category));
    return catalog;
  }, [catalog, tab]);

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setFormErrors([]);
    setShowAdvancedOAuth(false);
  }

  function openAdd(kindItem) {
    if (readOnly) return;
    const item = kindItem || kindOptions[0];
    if (!item) return;
    setEditingId(null);
    setFormKind(`${item.category}::${item.kind}`);
    setFormLabel("default");
    setFormFields(emptyFields(item));
    setFormDefault(true);
    setShowAdvancedOAuth(false);
    setShowForm(true);
  }

  function openEdit(entry) {
    if (readOnly) return;
    const spec = catalog.find((k) => k.category === entry.category && k.kind === entry.kind);
    setEditingId(entry.id);
    setFormKind(`${entry.category}::${entry.kind}`);
    setFormLabel(entry.label || "default");
    const initial = emptyFields(spec);
    if (entry.fields && typeof entry.fields === "object") {
      Object.keys(entry.fields).forEach((k) => {
        if (entry.fields[k] !== undefined && entry.fields[k] !== null) {
          initial[k] = entry.fields[k];
        }
      });
    }
    if (entry.meta && typeof entry.meta === "object") {
      Object.keys(entry.meta).forEach((k) => {
        if (initial[k] === "" && entry.meta[k]) {
          initial[k] = entry.meta[k];
        }
      });
    }
    setFormFields(initial);
    setFormDefault(!!entry.is_default);
    setShowAdvancedOAuth(false);
    setShowForm(true);
  }

  function validateFormFields(category, kind, spec, isEdit) {
    const fieldDefs = [
      ...(spec?.fields || []),
      ...(showAdvancedOAuth ? spec?.advanced_fields || [] : []),
    ];
    const errors = [];
    fieldDefs.forEach((f) => {
      const val = formFields[f.key];
      const trimmed = String(val || "").trim();
      if (!isEdit && f.required && !trimmed) errors.push(`${f.label} is required`);
      if (trimmed && isPlaceholderField(category, f.key, val)) errors.push(`${f.label} looks like example/hint text`);
    });
    return errors;
  }

  function buildFieldsPayload(spec) {
    const fieldDefs = [
      ...(spec?.fields || []),
      ...(showAdvancedOAuth ? spec?.advanced_fields || [] : []),
    ];
    const fields = {};
    fieldDefs.forEach((f) => {
      const val = String(formFields[f.key] || "").trim();
      if (val) fields[f.key] = formFields[f.key];
    });
    return fields;
  }

  const selectedSpec =
    kindOptions.find((k) => `${k.category}::${k.kind}` === formKind) ||
    catalog.find((k) => `${k.category}::${k.kind}` === formKind) ||
    kindOptions[0];

  const isGuidedGmailOAuth =
    selectedSpec?.setup === "guided" && selectedSpec?.kind === "gmail_oauth" && !editingId;
  const isTelegramBot =
    selectedSpec?.category === "telegram" && selectedSpec?.kind === "telegram_bot";
  const hasGoogleClientCreds =
    String(formFields.client_id || "").trim() && String(formFields.client_secret || "").trim();
  const canSaveGuidedOAuth =
    hasGoogleClientCreds ||
    (showAdvancedOAuth &&
      (String(formFields.refresh_token || "").trim() || String(formFields.access_token || "").trim()));

  async function handleCreate(e) {
    e.preventDefault();
    const [category, kind] = (formKind || "").split("::");
    if (!category || !kind) return;
    const spec = kindOptions.find((k) => k.category === category && k.kind === kind) ||
      catalog.find((k) => k.category === category && k.kind === kind);
    const errors = validateFormFields(category, kind, spec, false);
    if (errors.length) {
      setFormErrors(errors);
      return;
    }
    setFormErrors([]);
    setBusy("create");
    setError("");
    setSuccess("");
    try {
      const created = await createCredential({
        category,
        kind,
        label: formLabel || "default",
        fields: buildFieldsPayload(spec),
        is_default: formDefault,
      });
      closeForm();
      if (category === "telegram" && kind === "telegram_bot") {
        const botName = created?.meta?.bot_username;
        setSuccess(
          botName
            ? `Telegram bot connected (@${botName}). Publish a workflow with a Telegram trigger to go live.`
            : "Telegram bot saved and verified. Publish a workflow with a Telegram trigger to go live."
        );
      } else {
        setSuccess("Credential created.");
      }
      await load({ silent: true });
    } catch (err) {
      setError(err.message || "Create failed");
    } finally {
      setBusy("");
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    if (!editingId) return;
    const [category, kind] = (formKind || "").split("::");
    const spec = catalog.find((k) => k.category === category && k.kind === kind);
    const errors = validateFormFields(category, kind, spec, true);
    if (errors.length) {
      setFormErrors(errors);
      return;
    }
    setFormErrors([]);
    setBusy("update");
    setError("");
    setSuccess("");
    try {
      const fields = buildFieldsPayload(spec);
      await updateCredential(editingId, {
        label: formLabel || "default",
        fields: Object.keys(fields).length ? fields : undefined,
        is_default: formDefault,
      });
      closeForm();
      setSuccess("Credential updated.");
      await load({ silent: true });
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusy("");
    }
  }

  async function handleVerify(id) {
    setBusy(id);
    setError("");
    setSuccess("");
    try {
      const res = await verifyCredential(id);
      if (res?.status === "error") {
        setError(humanizeCredentialError(res.detail || "Verify failed"));
      } else {
        const okMsg = (res?.detail || "").trim();
        setSuccess(okMsg ? `Verified — ${okMsg}` : "Credential verified successfully.");
      }
      await load({ silent: true });
    } catch (err) {
      setError(humanizeCredentialError(err.message || "Verify failed"));
    } finally {
      setBusy("");
    }
  }

  async function handleDefault(id) {
    setBusy(id);
    setError("");
    setSuccess("");
    try {
      await setDefaultCredential(id);
      setSuccess("Default credential updated.");
      await load({ silent: true });
    } catch (err) {
      setError(err.message || "Failed");
    } finally {
      setBusy("");
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this credential?")) return;
    setBusy(id);
    setError("");
    setSuccess("");
    try {
      await deleteCredential(id);
      setSuccess("Credential deleted.");
      await load({ silent: true });
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setBusy("");
    }
  }

  async function handleCreateApiKey(e) {
    e.preventDefault();
    setBusy("apikey");
    setError("");
    setSuccess("");
    try {
      const res = await createApiKey({ name: newKeyName || "API key" });
      setCreatedRawKey(res?.key || "");
      setSuccess("Platform API key created — copy it now.");
      await load({ silent: true });
    } catch (err) {
      setError(err.message || "API key create failed");
    } finally {
      setBusy("");
    }
  }

  async function handleRevokeApiKey(id) {
    if (!window.confirm("Revoke this platform API key?")) return;
    setBusy(`apikey-${id}`);
    setError("");
    setSuccess("");
    try {
      await deleteApiKey({ id });
      setSuccess("Platform API key revoked.");
      await load({ silent: true });
    } catch (err) {
      setError(err.message || "Revoke failed");
    } finally {
      setBusy("");
    }
  }

  const oauthHint = OAUTH_FORM_HINTS[formKind];

  return (
    <WorkspacePageShell user={user} loading={!user || loading} loadingMessage="Loading credentials…">
      <WorkspaceHero
        eyebrow="Credentials"
        title="Keys, models & integrations"
        description="Store multiple named credentials per type — Gmail accounts, LLM APIs, Telegram bots, and more. Chat can save secrets here automatically."
      />

      {readOnly && (
        <WorkspaceAlert type="warn" className="mt-4">
          Viewer access — you can inspect credentials but cannot add, edit, or verify them.
        </WorkspaceAlert>
      )}

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

      {error ? <WorkspaceAlert type="error" className="mt-4">{error}</WorkspaceAlert> : null}
      {success ? <WorkspaceAlert type="success" className="mt-4">{success}</WorkspaceAlert> : null}

      <div className="mt-6 flex flex-wrap gap-2">
        {CATEGORY_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              tab === t.id
                ? "bg-neutral-900 text-white"
                : "border border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <div className="mt-8 space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <WorkspaceStatCard label="Total credentials" value={overview?.total ?? entries.length} />
            <WorkspaceStatCard
              label="Categories"
              value={Object.keys(overview?.by_category || {}).length}
            />
            <WorkspaceStatCard
              label="Suggested missing"
              value={(overview?.missing_suggested || []).join(", ") || "None"}
            />
          </div>
          <div className="rounded-2xl border border-neutral-200 bg-white p-6">
            <h3 className="text-lg font-semibold text-neutral-900">Quick start</h3>
            <p className="mt-2 text-sm text-neutral-500">
              Add multiple Gmails under Email, multiple LLM keys under AI / Models, or paste
              secrets in chat like <code className="rounded bg-neutral-100 px-1">telegram token:=…</code>.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {!readOnly && (
                <>
                  <button type="button" className="btn-primary !py-2 !text-sm" onClick={() => { setTab("llm"); openAdd(); }}>
                    Add LLM key
                  </button>
                  <button type="button" className="btn-secondary !py-2 !text-sm" onClick={() => { setTab("email"); setTimeout(() => openAdd(), 0); }}>
                    Add Gmail / SMTP
                  </button>
                </>
              )}
              <Link href="/workflows?tab=digests" className="btn-secondary !py-2 !text-sm">
                Scheduled digests
              </Link>
            </div>
          </div>
        </div>
      ) : null}

      {tab === "digests" ? (
        <div className="mt-8 rounded-2xl border border-neutral-200 bg-white p-6">
          <h3 className="text-lg font-semibold">Scheduled digests</h3>
          <p className="mt-2 text-sm text-neutral-500">
            Digest schedules live under Workflows. Delivery secrets stay in this Credentials vault
            (pick which Gmail/Telegram account on the notify node).
          </p>
          <Link href="/workflows?tab=digests" className="btn-primary mt-4 inline-flex !py-2.5 !text-sm">
            Open digest studio
          </Link>
        </div>
      ) : null}

      {tab === "api_keys" ? (
        <div className="mt-8 space-y-4">
          {!canManageApiKeys ? (
            <WorkspaceAlert type="info">
              Platform API keys require developer role or higher in this workspace.
            </WorkspaceAlert>
          ) : (
            <form onSubmit={handleCreateApiKey} className="flex flex-wrap items-end gap-3 rounded-2xl border border-neutral-200 bg-white p-5">
              <label className="block text-sm">
                <span className="text-neutral-500">Name</span>
                <input
                  className="mt-1 block w-56 rounded-lg border border-neutral-200 px-3 py-2"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                />
              </label>
              <button type="submit" className="btn-primary !py-2 !text-sm" disabled={busy === "apikey"}>
                Create platform key
              </button>
            </form>
          )}
          {createdRawKey ? (
            <WorkspaceAlert type="warn">
              Copy now — shown once: <code className="break-all">{createdRawKey}</code>
            </WorkspaceAlert>
          ) : null}
          {loading ? (
            <WorkspaceSkeletonList count={2} height="h-16" />
          ) : apiKeys.length === 0 ? (
            <WorkspaceEmpty
              title="No platform keys"
              description={
                canManageApiKeys
                  ? "Create a key to authenticate API requests against NovaFlow."
                  : "Ask a workspace developer or admin to create platform keys."
              }
            />
          ) : (
            <ul className="space-y-2">
              {apiKeys.map((k) => (
                <li key={k.id} className="flex items-center justify-between rounded-xl border border-neutral-200 bg-white px-4 py-3">
                  <div>
                    <p className="font-medium">{k.name}</p>
                    <p className="text-xs text-neutral-500">{k.key_prefix}…</p>
                  </div>
                  {canManageApiKeys ? (
                    <button
                      type="button"
                      className="text-sm text-red-600 disabled:opacity-50"
                      onClick={() => handleRevokeApiKey(k.id)}
                      disabled={busy === `apikey-${k.id}`}
                    >
                      Revoke
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      {["llm", "email", "messaging", "devtools"].includes(tab) ? (
        <div className="mt-8 space-y-4">
          {tab === "messaging" ? (
            <p className="rounded-xl border border-teal-100 bg-teal-50/80 px-4 py-3 text-sm text-teal-900">
              <strong>Telegram:</strong> paste the bot token from @BotFather, set a label, and save — we verify the bot
              and fetch its username automatically. Then build a workflow with a <strong>Trigger (Telegram)</strong> node
              and a <strong>Telegram notify</strong> reply node, and publish.
            </p>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-neutral-500">
              {filtered.length} credential{filtered.length === 1 ? "" : "s"} — multiple names allowed per type
            </p>
            {!readOnly ? (
              <button type="button" className="btn-primary !py-2 !text-sm" onClick={() => openAdd()}>
                Add credential
              </button>
            ) : null}
          </div>

          {showForm ? (
            <form
              onSubmit={editingId ? handleUpdate : handleCreate}
              className="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5"
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm">
                  <span className="text-neutral-500">Type</span>
                  <select
                    className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 disabled:bg-neutral-50"
                    value={formKind || `${selectedSpec?.category}::${selectedSpec?.kind}`}
                    onChange={(e) => {
                      setFormKind(e.target.value);
                      const spec = kindOptions.find((k) => `${k.category}::${k.kind}` === e.target.value);
                      setFormFields(emptyFields(spec));
                    }}
                    disabled={!!editingId}
                  >
                    {kindOptions.map((k) => (
                      <option key={`${k.category}-${k.kind}`} value={`${k.category}::${k.kind}`}>
                        {k.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="text-neutral-500">Label (e.g. work, ops)</span>
                  <input
                    className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2"
                    value={formLabel}
                    onChange={(e) => setFormLabel(e.target.value)}
                    required
                  />
                </label>
              </div>
              {formErrors.length > 0 ? (
                <ul className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">
                  {formErrors.map((msg) => (
                    <li key={msg}>{msg}</li>
                  ))}
                </ul>
              ) : null}
              {isGuidedGmailOAuth ? (
                <p className="text-xs text-neutral-500">
                  Enter Client ID and Client secret from Google Cloud, click <strong>Save credential</strong>, then use
                  Connect with Google.
                </p>
              ) : null}
              {isTelegramBot && !editingId ? (
                <p className="text-xs text-neutral-500">
                  Paste the token from @BotFather, choose a label (e.g. <em>support-bot</em>), and save — bot username
                  is filled automatically.
                </p>
              ) : null}
              {(selectedSpec?.fields || []).map((f) => (
                <label key={f.key} className="block text-sm">
                  <span className="text-neutral-500">{f.label}{f.required && !editingId ? " *" : ""}</span>
                  <input
                    type={f.secret ? "password" : "text"}
                    className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2"
                    value={formFields[f.key] || ""}
                    onChange={(e) => setFormFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                    required={!!f.required && !editingId}
                    placeholder={
                      f.placeholder ||
                      (editingId && f.secret ? "Leave blank to keep current" : undefined)
                    }
                    autoComplete="off"
                  />
                </label>
              ))}
              {(selectedSpec?.oauth ||
                selectedSpec?.setup === "guided" ||
                (selectedSpec?.category === "email" && selectedSpec?.kind === "gmail_oauth") ||
                (selectedSpec?.category === "google" && selectedSpec?.kind === "google_oauth")) && (
                <OAuthSetupPanel setup={oauthSetup} onConnectGmail={readOnly ? undefined : startGmailOAuth} />
              )}
              {oauthHint ? (
                <p className="text-xs text-neutral-500">{oauthHint}</p>
              ) : null}
              {(selectedSpec?.advanced_fields || []).length > 0 ? (
                <button
                  type="button"
                  className="text-xs font-semibold text-neutral-600 underline"
                  onClick={() => setShowAdvancedOAuth((v) => !v)}
                >
                  {showAdvancedOAuth ? "Hide advanced token fields" : "Show advanced token fields"}
                </button>
              ) : null}
              {showAdvancedOAuth &&
                (selectedSpec?.advanced_fields || []).map((f) => (
                  <label key={f.key} className="block text-sm">
                    <span className="text-neutral-500">{f.label}{f.required && !editingId ? " *" : ""}</span>
                    <input
                      type={f.secret ? "password" : "text"}
                      className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2"
                      value={formFields[f.key] || ""}
                      onChange={(e) => setFormFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                      required={!!f.required && !editingId}
                      placeholder={editingId && f.secret ? "Leave blank to keep current" : undefined}
                      autoComplete="off"
                    />
                  </label>
                ))}
              <label className="flex items-center gap-2 text-sm text-neutral-700">
                <input type="checkbox" checked={formDefault} onChange={(e) => setFormDefault(e.target.checked)} />
                Set as default for this type
              </label>
              <div className="flex gap-2">
                {!isGuidedGmailOAuth || canSaveGuidedOAuth || editingId ? (
                  <button
                    type="submit"
                    className="btn-primary !py-2 !text-sm"
                    disabled={busy === "create" || busy === "update"}
                  >
                    {editingId ? "Save changes" : "Save credential"}
                  </button>
                ) : null}
                <button type="button" className="btn-secondary !py-2 !text-sm" onClick={closeForm}>
                  Cancel
                </button>
              </div>
            </form>
          ) : null}

          {loading ? (
            <WorkspaceSkeletonList count={3} />
          ) : filtered.length === 0 && !loadError ? (
            <WorkspaceEmpty
              title="No credentials yet"
              description="Add one here, or paste secrets in chat and NovaFlow will store them in the vault."
              actionLabel={readOnly ? undefined : "Add credential"}
              onAction={readOnly ? undefined : () => openAdd()}
            />
          ) : filtered.length > 0 ? (
            <ul className="space-y-3">
              {filtered.map((entry) => (
                <li key={entry.id} className="rounded-2xl border border-neutral-200 bg-white p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-neutral-900">
                        {entry.label}{" "}
                        {entry.is_default ? (
                          <span className="ml-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                            default
                          </span>
                        ) : null}
                      </p>
                      <p className="mt-1 text-xs text-neutral-500">
                        {entry.category} / {entry.kind} · status: {entry.status}
                      </p>
                      <p className="mt-2 text-xs text-neutral-400">
                        {Object.entries(entry.meta || {})
                          .filter(([k]) => k.endsWith("_mask") || k.endsWith("_configured") || !k.includes("_"))
                          .slice(0, 6)
                          .map(([k, v]) => `${k}=${String(v)}`)
                          .join(" · ")}
                      </p>
                    </div>
                    {!readOnly ? (
                      <div className="flex flex-wrap gap-2">
                        <button type="button" className="btn-secondary !py-1.5 !text-xs" onClick={() => openEdit(entry)} disabled={!!busy}>
                          Edit
                        </button>
                        {!entry.is_default ? (
                          <button type="button" className="btn-secondary !py-1.5 !text-xs" onClick={() => handleDefault(entry.id)} disabled={!!busy}>
                            Set default
                          </button>
                        ) : null}
                        <button type="button" className="btn-secondary !py-1.5 !text-xs" onClick={() => handleVerify(entry.id)} disabled={!!busy}>
                          Verify
                        </button>
                        <button type="button" className="text-xs text-red-600" onClick={() => handleDelete(entry.id)} disabled={!!busy}>
                          Delete
                        </button>
                      </div>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </WorkspacePageShell>
  );
}
