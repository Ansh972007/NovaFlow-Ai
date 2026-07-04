"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import LiveBackground from "@/components/LiveBackground";
import { getUserInfo } from "@/lib/api/auth";
import {
  createKnowledge,
  getEmbeddingModels,
  listKnowledge,
} from "@/lib/api/knowledge";

const ease = [0.16, 1, 0.3, 1];

export default function KnowledgeListClient() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [model, setModel] = useState("");
  const [models, setModels] = useState([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listKnowledge({ pageSize: 50 });
      setItems(res?.data || []);
      setTotal(res?.total || 0);
    } catch {
      setItems([]);
      setTotal(0);
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
    if (!user) return;
    load();
    getEmbeddingModels()
      .then((res) => {
        const list = res?.models || [];
        setModels(list);
        if (list.length) setModel(String(list[0]));
      })
      .catch(() => setModels([]));
  }, [user, load]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      const kb = await createKnowledge({
        name: name.trim(),
        description: description.trim(),
        model: model || undefined,
        type: 0,
      });
      setShowCreate(false);
      setName("");
      setDescription("");
      router.push(`/knowledge/${kb.id}`);
    } catch (err) {
      setError(err.message || "Failed to create knowledge base");
    } finally {
      setCreating(false);
    }
  }

  if (!user) {
    return (
      <div className="relative flex min-h-screen items-center justify-center">
        <LiveBackground variant="subtle" showNetwork />
        <span className="relative z-10 text-muted">Loading…</span>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <LiveBackground variant="subtle" showNetwork mouseTracking />
      <div className="relative z-10">
        <AppHeader user={user} />

        <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
            className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between"
          >
            <div>
              <p className="text-xs font-semibold tracking-[0.2em] text-muted uppercase">
                Knowledge
              </p>
              <h1 className="mt-2 font-serif text-4xl tracking-tight">Document libraries</h1>
              <p className="mt-2 max-w-lg text-sm text-muted">
                Upload PDFs and docs to ground your AI assistants with accurate answers.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="btn-primary shrink-0"
            >
              + New knowledge base
            </button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.5, ease }}
            className="mt-10"
          >
            {loading ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="glass-card h-32 animate-pulse rounded-2xl" />
                ))}
              </div>
            ) : items.length === 0 ? (
              <div className="glass-card rounded-2xl p-12 text-center">
                <p className="text-lg font-medium">No knowledge bases yet</p>
                <p className="mt-2 text-sm text-muted">
                  Create one to start uploading documents for RAG.
                </p>
                <button
                  type="button"
                  onClick={() => setShowCreate(true)}
                  className="btn-primary mt-6"
                >
                  Create your first library
                </button>
              </div>
            ) : (
              <>
                <p className="mb-4 text-xs text-muted">{total} knowledge base{total !== 1 ? "s" : ""}</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  {items.map((kb, i) => (
                    <motion.div
                      key={kb.id}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.05 * i, ease }}
                    >
                      <Link
                        href={`/knowledge/${kb.id}`}
                        className="glass-card card-hover block rounded-2xl p-6"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <span className="text-2xl">📚</span>
                          <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] text-muted">
                            {kb.state === 1 ? "Published" : "Draft"}
                          </span>
                        </div>
                        <h2 className="mt-4 font-semibold">{kb.name}</h2>
                        <p className="mt-1 line-clamp-2 text-sm text-muted">
                          {kb.description || "No description"}
                        </p>
                        <p className="mt-4 text-[11px] text-muted-light">
                          Updated {kb.update_time ? new Date(kb.update_time).toLocaleDateString() : "—"}
                        </p>
                      </Link>
                    </motion.div>
                  ))}
                </div>
              </>
            )}
          </motion.div>
        </main>
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-2xl"
          >
            <h2 className="font-serif text-2xl">New knowledge base</h2>
            <p className="mt-1 text-sm text-muted">Store documents for retrieval-augmented chat.</p>

            <form onSubmit={handleCreate} className="mt-6 space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium">Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-field w-full"
                  placeholder="Support docs"
                  required
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input-field w-full resize-none"
                  rows={2}
                  placeholder="Optional"
                />
              </div>
              {models.length > 0 && (
                <div>
                  <label className="mb-1.5 block text-sm font-medium">Embedding model</label>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="input-field w-full"
                  >
                    {models.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {error && (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                  {error}
                </p>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 rounded-full border border-border py-2.5 text-sm font-medium hover:bg-surface"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="auth-submit-btn flex-1 rounded-full py-2.5 text-sm font-semibold disabled:opacity-50"
                >
                  {creating ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
}
