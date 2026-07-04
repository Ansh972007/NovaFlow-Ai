"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import AppHeader from "@/components/AppHeader";
import LiveBackground from "@/components/LiveBackground";
import { getUserInfo } from "@/lib/api/auth";
import {
  FILE_STATUS,
  getKnowledgeFiles,
  listKnowledge,
  processKnowledgeFiles,
  uploadKnowledgeFile,
} from "@/lib/api/knowledge";

const ease = [0.16, 1, 0.3, 1];
const POLL_MS = 4000;

export default function KnowledgeDetailClient({ knowledgeId }) {
  const router = useRouter();
  const fileInputRef = useRef(null);
  const [user, setUser] = useState(null);
  const [kb, setKb] = useState(null);
  const [files, setFiles] = useState([]);
  const [writeable, setWriteable] = useState(true);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");

  const loadFiles = useCallback(async () => {
    try {
      const res = await getKnowledgeFiles(knowledgeId, { pageSize: 100 });
      setFiles(res?.data || []);
      setWriteable(res?.writeable !== false);
    } catch (err) {
      setError(err.message);
    }
  }, [knowledgeId]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listKnowledge({ pageSize: 100 });
      const found = (res?.data || []).find((k) => String(k.id) === String(knowledgeId));
      setKb(found || { id: knowledgeId, name: `Knowledge #${knowledgeId}` });
      await loadFiles();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [knowledgeId, loadFiles]);

  useEffect(() => {
    getUserInfo()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    load();
  }, [user, load]);

  useEffect(() => {
    if (!user || loading) return;
    const hasProcessing = files.some((f) => [1, 4, 5].includes(f.status));
    if (!hasProcessing) return;
    const id = setInterval(loadFiles, POLL_MS);
    return () => clearInterval(id);
  }, [user, loading, files, loadFiles]);

  async function handleUpload(e) {
    const selected = Array.from(e.target.files || []);
    if (!selected.length) return;
    setUploading(true);
    setError("");
    setUploadProgress(0);

    try {
      for (let i = 0; i < selected.length; i++) {
        const file = selected[i];
        const uploaded = await uploadKnowledgeFile(knowledgeId, file, (evt) => {
          const base = (i / selected.length) * 100;
          const part = evt.total ? (evt.loaded / evt.total) * (100 / selected.length) : 0;
          setUploadProgress(Math.round(base + part));
        });

        if (uploaded?.file_path) {
          await processKnowledgeFiles(knowledgeId, [uploaded.file_path]);
        }
      }
      await loadFiles();
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
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

        <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
          <Link
            href="/knowledge"
            className="group mb-6 inline-flex items-center gap-2 text-sm text-muted hover:text-foreground"
          >
            <span className="transition-transform group-hover:-translate-x-1">←</span>
            All knowledge bases
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
            className="glass-card rounded-2xl p-6 sm:p-8"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold tracking-widest text-muted uppercase">
                  Knowledge base
                </p>
                <h1 className="mt-2 font-serif text-3xl tracking-tight">
                  {loading ? "Loading…" : kb?.name}
                </h1>
                {kb?.description && (
                  <p className="mt-2 text-sm text-muted">{kb.description}</p>
                )}
              </div>
              {writeable && (
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.pptx"
                    className="hidden"
                    onChange={handleUpload}
                  />
                  <button
                    type="button"
                    disabled={uploading}
                    onClick={() => fileInputRef.current?.click()}
                    className="btn-primary whitespace-nowrap disabled:opacity-50"
                  >
                    {uploading ? `Uploading ${uploadProgress}%` : "+ Upload files"}
                  </button>
                </div>
              )}
            </div>

            {uploading && (
              <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-surface">
                <motion.div
                  className="h-full bg-black"
                  animate={{ width: `${uploadProgress}%` }}
                  transition={{ ease: "linear" }}
                />
              </div>
            )}

            {error && (
              <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                {error}
              </p>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, ease }}
            className="mt-8"
          >
            <h2 className="mb-4 text-sm font-semibold tracking-wide text-muted uppercase">
              Documents ({files.length})
            </h2>

            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="glass-card h-16 animate-pulse rounded-xl" />
                ))}
              </div>
            ) : files.length === 0 ? (
              <div className="glass-card rounded-2xl p-10 text-center">
                <p className="font-medium">No documents yet</p>
                <p className="mt-2 text-sm text-muted">
                  Upload PDF, Word, or text files to index them for AI search.
                </p>
              </div>
            ) : (
              <ul className="space-y-3">
                {files.map((file, i) => {
                  const status = FILE_STATUS[file.status] || FILE_STATUS[5];
                  return (
                    <motion.li
                      key={file.id || file.file_name}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04, ease }}
                      className="glass-card flex items-center justify-between gap-4 rounded-xl px-5 py-4"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-medium">{file.file_name}</p>
                        <p className="mt-0.5 text-[11px] text-muted">
                          {file.update_time
                            ? new Date(file.update_time).toLocaleString()
                            : "—"}
                        </p>
                      </div>
                      <span
                        className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-semibold ${status.color}`}
                      >
                        {status.label}
                      </span>
                    </motion.li>
                  );
                })}
              </ul>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="mt-8 rounded-2xl border border-border bg-white/60 p-5 text-sm text-muted"
          >
            <p className="font-medium text-foreground">How it works</p>
            <ol className="mt-2 list-inside list-decimal space-y-1 text-[13px]">
              <li>Upload documents — they are chunked and embedded automatically.</li>
              <li>Status turns <span className="text-green-700">Ready</span> when indexing completes.</li>
              <li>Link this library to an assistant in your workspace to enable RAG chat.</li>
            </ol>
            <Link href="/chat" className="mt-4 inline-flex text-sm font-semibold text-foreground hover:underline">
              Open chat →
            </Link>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
