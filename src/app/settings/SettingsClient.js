"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import { getUserInfo } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import { getAllLlm, getAssistantLlmConfig, getKnowledgeLlmConfig } from "@/lib/api/llm";
import { getApiBaseUrl } from "@/lib/api/config";
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

  function handleRerunSetup() {
    resetSetup();
    router.push("/setup");
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
