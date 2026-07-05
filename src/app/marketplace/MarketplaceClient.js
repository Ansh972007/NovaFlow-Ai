"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppHeader from "@/components/AppHeader";
import WorkspaceLiveBackground from "@/components/WorkspaceLiveBackground";
import { getUserInfo } from "@/lib/api/auth";
import { cloneMarketplaceWorkflow, listMarketplaceWorkflows } from "@/lib/api/marketplace";

export default function MarketplaceClient() {
  const [user, setUser] = useState(null);
  const [items, setItems] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getUserInfo()
      .then((u) => {
        setUser(u);
        return listMarketplaceWorkflows();
      })
      .then((res) => {
        setItems(res?.items || []);
        setTemplates(res?.templates || []);
      })
      .catch(() => {});
  }, []);

  async function handleClone(id) {
    setBusy(true);
    try {
      const w = await cloneMarketplaceWorkflow(id);
      if (w?.id) window.location.href = `/workflows/${w.id}`;
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <WorkspaceLiveBackground />
      <div className="relative z-10">
        <AppHeader user={user} />
        <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
          <h1 className="font-serif text-3xl tracking-tight">Marketplace</h1>
          <p className="mt-2 text-neutral-500">Clone public workflows shared by the community.</p>

          <section className="mt-8">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">Public workflows</h2>
            {items.length === 0 ? (
              <p className="mt-4 text-sm text-neutral-500">No public workflows yet. Publish one from the workflow builder.</p>
            ) : (
              <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                {items.map((w) => (
                  <li key={w.id} className="workspace-panel rounded-2xl p-5">
                    <p className="font-semibold">{w.name}</p>
                    <p className="mt-1 text-sm text-neutral-500 line-clamp-2">{w.desc}</p>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleClone(w.id)}
                      className="btn-secondary mt-4 text-xs"
                    >
                      Clone to workspace
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-10">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">Built-in templates</h2>
            <ul className="mt-4 grid gap-3 sm:grid-cols-3">
              {templates.map((t) => (
                <li key={t.id} className="rounded-xl border border-black/[0.06] bg-white/60 p-4">
                  <p className="font-medium">{t.name}</p>
                  <p className="mt-1 text-xs text-neutral-500">{t.desc}</p>
                  <Link href="/workflows" className="mt-3 inline-block text-xs font-semibold hover:underline">
                    Create from template →
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </main>
      </div>
    </div>
  );
}
