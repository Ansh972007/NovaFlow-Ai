"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Logo from "@/components/Logo";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import { getUserInfo } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import { createAssistant, setAssistantStatus, setAssistantKnowledge } from "@/lib/api/apps";
import { createKnowledge, getEmbeddingModels } from "@/lib/api/knowledge";
import { ASSISTANT_TEMPLATES } from "@/lib/setup/templates";
import { markSetupComplete } from "@/lib/setup/storage";
import { getApiBaseUrl } from "@/lib/api/config";

const ease = [0.16, 1, 0.3, 1];
const STEPS = ["Welcome", "API", "Assistant", "Done"];

export default function SetupClient() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [checking, setChecking] = useState(false);
  const [templateId, setTemplateId] = useState(ASSISTANT_TEMPLATES[0].id);
  const [assistantName, setAssistantName] = useState(ASSISTANT_TEMPLATES[0].name);
  const [kbName, setKbName] = useState("My Documents");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [createdAppId, setCreatedAppId] = useState(null);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  async function runHealthCheck() {
    setChecking(true);
    setError("");
    try {
      const result = await checkBackendHealth();
      setHealth(result);
      if (!result.ok) setError("NovaFlow API is not reachable. Start the backend and try again.");
    } catch {
      setHealth({ ok: false });
      setError("Health check failed.");
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    if (step === 1 && health === null) runHealthCheck();
  }, [step]);

  function selectTemplate(id) {
    setTemplateId(id);
    const t = ASSISTANT_TEMPLATES.find((x) => x.id === id);
    if (t) {
      setAssistantName(t.name);
    }
  }

  async function finishSetup() {
    setCreating(true);
    setError("");
    const template = ASSISTANT_TEMPLATES.find((t) => t.id === templateId) || ASSISTANT_TEMPLATES[0];
    try {
      const assistant = await createAssistant({
        name: assistantName.trim() || template.name,
        prompt: template.prompt,
        logo: "",
      });
      await setAssistantStatus(assistant.id, 1);

      try {
        const emb = await getEmbeddingModels();
        const model = emb?.models?.[0];
        if (kbName.trim() && model) {
          const kb = await createKnowledge({
            name: kbName.trim(),
            description: "Created during NovaFlow setup",
            model: String(model),
            type: 0,
          });
          if (kb?.id) {
            await setAssistantKnowledge(assistant.id, [kb.id]);
          }
        }
      } catch {
        /* KB optional if embedding not configured */
      }

      setCreatedAppId(assistant.id);
      markSetupComplete();
      setStep(3);
    } catch (err) {
      setError(err.message || "Setup failed");
    } finally {
      setCreating(false);
    }
  }

  function skipToDashboard() {
    markSetupComplete();
    router.push("/dashboard");
  }

  if (!user) {
    return (
      <div className="relative flex min-h-screen items-center justify-center">
        <WorkspaceLiveBackground />
        <span className="relative z-10 text-neutral-500">Loading…</span>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10 mx-auto flex min-h-screen max-w-lg flex-col px-4 py-10 sm:px-6">
        <Logo size="sm" />

        <div className="mt-8 flex gap-2">
          {STEPS.map((label, i) => (
            <div
              key={label}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i <= step ? "bg-foreground" : "bg-border"
              }`}
              title={label}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          {step === 0 && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ ease }}
              className="workspace-panel mt-8 flex flex-1 flex-col rounded-[1.75rem] p-8"
            >
              <h1 className="font-serif text-3xl tracking-tight">Welcome to NovaFlow</h1>
              <p className="mt-3 text-muted">
                Hi {user.user_name}! Let&apos;s connect your workspace in a few quick steps.
              </p>
              <ul className="mt-6 space-y-2 text-sm text-muted">
                <li>✓ Verify API connection</li>
                <li>✓ Create your first assistant</li>
                <li>✓ Optional knowledge base</li>
              </ul>
              <div className="mt-auto flex gap-3 pt-8">
                <button type="button" onClick={skipToDashboard} className="text-sm text-muted hover:text-foreground">
                  Skip for now
                </button>
                <button type="button" onClick={() => setStep(1)} className="btn-primary ml-auto">
                  Get started
                </button>
              </div>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div
              key="api"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="workspace-panel mt-8 flex flex-1 flex-col rounded-[1.75rem] p-8"
            >
              <h2 className="text-xl font-semibold">Connect API</h2>
              <p className="mt-2 text-sm text-muted">
                NovaFlow talks to your backend at{" "}
                <code className="rounded bg-surface px-1.5 py-0.5 text-xs">{getApiBaseUrl()}</code>
              </p>
              <div className="mt-6 rounded-xl border border-border bg-white/80 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">API status</span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${
                      health?.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                    }`}
                  >
                    {checking ? "Checking…" : health?.ok ? "Online" : "Offline"}
                  </span>
                </div>
              </div>
              {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
              <div className="mt-auto flex gap-3 pt-8">
                <button type="button" onClick={() => setStep(0)} className="text-sm text-muted">
                  Back
                </button>
                <button type="button" onClick={runHealthCheck} disabled={checking} className="text-sm font-medium">
                  Retry
                </button>
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  disabled={!health?.ok}
                  className="btn-primary ml-auto disabled:opacity-40"
                >
                  Continue
                </button>
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="assistant"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="workspace-panel mt-8 flex flex-1 flex-col rounded-[1.75rem] p-8"
            >
              <h2 className="text-xl font-semibold">Choose a template</h2>
              <div className="mt-4 space-y-2">
                {ASSISTANT_TEMPLATES.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => selectTemplate(t.id)}
                    className={`flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-colors ${
                      templateId === t.id ? "border-foreground bg-surface" : "border-border hover:bg-surface/50"
                    }`}
                  >
                    <span className="text-xl">{t.icon}</span>
                    <div>
                      <p className="font-medium">{t.name}</p>
                      <p className="text-xs text-muted">{t.description}</p>
                    </div>
                  </button>
                ))}
              </div>
              <label className="mt-4 block text-sm font-medium">
                Assistant name
                <input
                  value={assistantName}
                  onChange={(e) => setAssistantName(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-border px-3 py-2 text-sm outline-none"
                />
              </label>
              <label className="mt-3 block text-sm font-medium">
                Knowledge base name <span className="font-normal text-muted">(optional)</span>
                <input
                  value={kbName}
                  onChange={(e) => setKbName(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-border px-3 py-2 text-sm outline-none"
                />
              </label>
              {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
              <div className="mt-auto flex gap-3 pt-8">
                <button type="button" onClick={() => setStep(1)} className="text-sm text-muted">
                  Back
                </button>
                <button
                  type="button"
                  onClick={finishSetup}
                  disabled={creating}
                  className="btn-primary ml-auto disabled:opacity-50"
                >
                  {creating ? "Setting up…" : "Finish setup"}
                </button>
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="workspace-panel mt-8 flex flex-1 flex-col rounded-[1.75rem] p-8 text-center"
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-50 text-2xl">
                ✓
              </div>
              <h2 className="mt-4 text-xl font-semibold">You&apos;re all set!</h2>
              <p className="mt-2 text-sm text-muted">
                Your assistant is published and ready to chat.
              </p>
              <div className="mt-8 flex flex-col gap-3">
                <Link
                  href={createdAppId ? `/apps/${createdAppId}` : "/apps"}
                  className="btn-secondary"
                >
                  Configure assistant
                </Link>
                <Link
                  href={createdAppId ? `/chat?app=${createdAppId}` : "/chat"}
                  className="btn-primary"
                >
                  Open Chat
                </Link>
                <Link href="/dashboard" className="text-sm font-medium text-muted hover:text-foreground">
                  Go to Dashboard
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
