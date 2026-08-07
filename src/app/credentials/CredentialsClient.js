"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { ensureActiveWorkspace } from "@/lib/api/workspaces";
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
      <div className="space-y-2">
        {(google.redirect_uris || []).map((row) => (
          <div key={row.id} className="rounded-lg bg-white/90 p-2 ring-1 ring-sky-100">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-700">{row.label}</p>
            <p className="mt-1 break-all font-mono text-[11px] text-neutral-700">{row.uri}</p>
            <button
              type="button"
              className="mt-1 text-xs font-semibold text-sky-800 underline"
              onClick={() => navigator.clipboard?.writeText(row.uri)}
            >
              Copy redirect URI
            </button>
          </div>
        ))}
      </div>
      {google.gmail_oauth_enabled && onConnectGmail ? (
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
  return out;
}

export default function CredentialsClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState("overview");
  const [catalog, setCatalog] = useState([]);
  const [entries, setEntries] = useState([]);
  const [overview, setOverview] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formKind, setFormKind] = useState("");
  const [formLabel, setFormLabel] = useState("default");
  const [formFields, setFormFields] = useState({});
  const [formDefault, setFormDefault] = useState(true);
  const [newKeyName, setNewKeyName] = useState("API key");
  const [createdRawKey, setCreatedRawKey] = useState("");
  const [oauthSetup, setOauthSetup] = useState(null);
  const [showAdvancedOAuth, setShowAdvancedOAuth] = useState(false);
  const [formErrors, setFormErrors] = useState([]);

  const isAdmin = user?.role === "admin" || user?.role === "super_admin" || user?.is_admin;

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [cat, list, ov, keys, oauth] = await Promise.all([
        getCredentialsCatalog().catch(() => []),
        listCredentials().catch(() => []),
        getCredentialsOverview().catch(() => null),
        listApiKeys().catch(() => []),
        getOAuthSetup().catch(() => null),
      ]);
      setCatalog(Array.isArray(cat) ? cat : []);
      setEntries(Array.isArray(list) ? list : []);
      setOverview(ov || null);
      setApiKeys(Array.isArray(keys) ? keys : []);
      setOauthSetup(oauth || null);
    } catch (e) {
      setError(e.message || "Failed to load credentials");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then(async (u) => {
        await ensureActiveWorkspace();
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

  function openAdd(kindItem) {
    const item = kindItem || kindOptions[0];
    if (!item) return;
    setFormKind(`${item.category}::${item.kind}`);
    setFormLabel("default");
    setFormFields(emptyFields(item));
    setFormDefault(true);
    setShowForm(true);
  }

  async function handleCreate(e) {
    e.preventDefault();
    const [category, kind] = (formKind || "").split("::");
    if (!category || !kind) return;
    const spec = kindOptions.find((k) => k.category === category && k.kind === kind);
    const fieldDefs = [
      ...(spec?.fields || []),
      ...(showAdvancedOAuth ? spec?.advanced_fields || [] : []),
    ];
    const errors = [];
    fieldDefs.forEach((f) => {
      const val = formFields[f.key];
      if (f.required && !String(val || "").trim()) errors.push(`${f.label} is required`);
      if (val && isPlaceholderField(category, f.key, val)) errors.push(`${f.label} looks like example/hint text`);
    });
    if (errors.length) {
      setFormErrors(errors);
      return;
    }
    setFormErrors([]);
    setBusy("create");
    setError("");
    try {
      await createCredential({
        category,
        kind,
        label: formLabel || "default",
        fields: formFields,
        is_default: formDefault,
      });
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.message || "Create failed");
    } finally {
      setBusy("");
    }
  }

  async function handleVerify(id) {
    setBusy(id);
    try {
      await verifyCredential(id);
      await load();
    } catch (err) {
      setError(err.message || "Verify failed");
    } finally {
      setBusy("");
    }
  }

  async function handleDefault(id) {
    setBusy(id);
    try {
      await setDefaultCredential(id);
      await load();
    } catch (err) {
      setError(err.message || "Failed");
    } finally {
      setBusy("");
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this credential?")) return;
    setBusy(id);
    try {
      await deleteCredential(id);
      await load();
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setBusy("");
    }
  }

  async function handleCreateApiKey(e) {
    e.preventDefault();
    setBusy("apikey");
    try {
      const res = await createApiKey({ name: newKeyName || "API key" });
      setCreatedRawKey(res?.key || "");
      await load();
    } catch (err) {
      setError(err.message || "API key create failed");
    } finally {
      setBusy("");
    }
  }

  const selectedSpec = kindOptions.find((k) => `${k.category}::${k.kind}` === formKind) || kindOptions[0];

  return (
    <WorkspacePageShell user={user} loading={!user || loading} loadingMessage="Loading credentials…">
      <WorkspaceHero
        eyebrow="Credentials"
        title="Keys, models & integrations"
        description="Store multiple named credentials per type — Gmail accounts, LLM APIs, Telegram bots, and more. Chat can save secrets here automatically."
      />

      {error ? <WorkspaceAlert variant="error">{error}</WorkspaceAlert> : null}

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
              <button type="button" className="btn-primary !py-2 !text-sm" onClick={() => { setTab("llm"); openAdd(); }}>
                Add LLM key
              </button>
              <button type="button" className="btn-secondary !py-2 !text-sm" onClick={() => { setTab("email"); setTimeout(() => openAdd(), 0); }}>
                Add Gmail / SMTP
              </button>
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
          {createdRawKey ? (
            <WorkspaceAlert>
              Copy now — shown once: <code className="break-all">{createdRawKey}</code>
            </WorkspaceAlert>
          ) : null}
          <ul className="space-y-2">
            {apiKeys.map((k) => (
              <li key={k.id} className="flex items-center justify-between rounded-xl border border-neutral-200 bg-white px-4 py-3">
                <div>
                  <p className="font-medium">{k.name}</p>
                  <p className="text-xs text-neutral-500">{k.key_prefix}…</p>
                </div>
                <button
                  type="button"
                  className="text-sm text-red-600"
                  onClick={async () => {
                    await deleteApiKey({ id: k.id });
                    await load();
                  }}
                >
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {["llm", "email", "messaging", "devtools"].includes(tab) ? (
        <div className="mt-8 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-neutral-500">
              {filtered.length} credential{filtered.length === 1 ? "" : "s"} — multiple names allowed per type
            </p>
            <button type="button" className="btn-primary !py-2 !text-sm" onClick={() => openAdd()} disabled={!isAdmin && false}>
              Add credential
            </button>
          </div>

          {showForm ? (
            <form onSubmit={handleCreate} className="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm">
                  <span className="text-neutral-500">Type</span>
                  <select
                    className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2"
                    value={formKind || `${selectedSpec?.category}::${selectedSpec?.kind}`}
                    onChange={(e) => {
                      setFormKind(e.target.value);
                      const spec = kindOptions.find((k) => `${k.category}::${k.kind}` === e.target.value);
                      setFormFields(emptyFields(spec));
                    }}
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
              {(selectedSpec?.oauth ||
                selectedSpec?.setup === "guided" ||
                (selectedSpec?.category === "email" && selectedSpec?.kind === "gmail_oauth") ||
                (selectedSpec?.category === "google" && selectedSpec?.kind === "google_oauth")) && (
                <OAuthSetupPanel setup={oauthSetup} onConnectGmail={startGmailOAuth} />
              )}
              {formErrors.length > 0 ? (
                <ul className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">
                  {formErrors.map((msg) => (
                    <li key={msg}>{msg}</li>
                  ))}
                </ul>
              ) : null}
              {selectedSpec?.setup === "guided" && selectedSpec?.kind === "gmail_oauth" ? (
                <p className="text-xs text-neutral-500">
                  Use Connect with Google above — token paste is optional under Advanced.
                </p>
              ) : null}
              {(selectedSpec?.fields || []).map((f) => (
                <label key={f.key} className="block text-sm">
                  <span className="text-neutral-500">{f.label}{f.required ? " *" : ""}</span>
                  <input
                    type={f.secret ? "password" : "text"}
                    className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2"
                    value={formFields[f.key] || ""}
                    onChange={(e) => setFormFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                    required={!!f.required}
                    autoComplete="off"
                  />
                </label>
              ))}
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
                    <span className="text-neutral-500">{f.label}{f.required ? " *" : ""}</span>
                    <input
                      type={f.secret ? "password" : "text"}
                      className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2"
                      value={formFields[f.key] || ""}
                      onChange={(e) => setFormFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                      required={!!f.required}
                      autoComplete="off"
                    />
                  </label>
                ))}
              <label className="flex items-center gap-2 text-sm text-neutral-700">
                <input type="checkbox" checked={formDefault} onChange={(e) => setFormDefault(e.target.checked)} />
                Set as default for this type
              </label>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary !py-2 !text-sm" disabled={busy === "create"}>
                  Save
                </button>
                <button type="button" className="btn-secondary !py-2 !text-sm" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
              </div>
            </form>
          ) : null}

          {loading ? (
            <p className="text-sm text-neutral-500">Loading…</p>
          ) : filtered.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-neutral-200 bg-white p-8 text-center text-sm text-neutral-500">
              No credentials yet. Add one, or paste secrets in chat.
            </p>
          ) : (
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
                    <div className="flex flex-wrap gap-2">
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
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </WorkspacePageShell>
  );
}
