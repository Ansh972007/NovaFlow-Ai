"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceBackLink from "@/components/workspace/WorkspaceBackLink";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import { FileIcon, KnowledgeIcon } from "@/components/workspace/WorkspaceIcons";
import { getUserInfo } from "@/lib/api/auth";
import {
  FILE_STATUS,
  KB_STATUS_LABELS,
  deleteKnowledgeFile,
  getKnowledgeById,
  getKnowledgeFiles,
  ingestKnowledgeUrl,
  processKnowledgeFiles,
  retryKnowledgeFile,
  uploadKnowledgeFile,
} from "@/lib/api/knowledge";
import KnowledgeQAPreview from "@/components/knowledge/KnowledgeQAPreview";
import KnowledgeSyncPanel from "@/components/knowledge/KnowledgeSyncPanel";
import KnowledgeGraphPanel from "@/components/knowledge/KnowledgeGraphPanel";
import { useWorkspaceAccess } from "@/lib/auth/workspaceAccess";

const ease = [0.16, 1, 0.3, 1];
const POLL_MS = 4000;

export default function KnowledgeDetailClient({ knowledgeId }) {
  const router = useRouter();
  const { readOnly: workspaceReadOnly } = useWorkspaceAccess();
  const fileInputRef = useRef(null);
  const [user, setUser] = useState(null);
  const [kb, setKb] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [files, setFiles] = useState([]);
  const [writeableFromApi, setWriteableFromApi] = useState(true);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [ingestUrl, setIngestUrl] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const loadFiles = useCallback(async () => {
    try {
      const res = await getKnowledgeFiles(knowledgeId, { pageSize: 100 });
      setFiles(res?.data || []);
      setWriteableFromApi(res?.writeable !== false);
    } catch (err) {
      setError(err.message);
    }
  }, [knowledgeId]);

  const load = useCallback(async () => {
    setLoading(true);
    setNotFound(false);
    try {
      const detail = await getKnowledgeById(knowledgeId);
      setKb(detail);
      await loadFiles();
    } catch (err) {
      setKb(null);
      if (err?.status === 404 || /not found/i.test(err.message || "")) {
        setNotFound(true);
      } else {
        setError(err.message || "Failed to load library");
      }
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

  async function handleRetry(file) {
    if (!file?.id || !writeable) return;
    setError("");
    try {
      await retryKnowledgeFile({ file_id: file.id });
      await loadFiles();
    } catch (err) {
      setError(err.message || "Retry failed");
    }
  }

  async function handleDelete(file) {
    if (!file?.id || !writeable) return;
    setDeletingId(file.id);
    setError("");
    try {
      await deleteKnowledgeFile(file.id);
      await loadFiles();
      const detail = await getKnowledgeById(knowledgeId);
      setKb(detail);
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

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
      const detail = await getKnowledgeById(knowledgeId);
      setKb(detail);
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleIngestUrl(e) {
    e.preventDefault();
    const url = ingestUrl.trim();
    if (!url) return;
    setIngesting(true);
    setError("");
    try {
      await ingestKnowledgeUrl(knowledgeId, url);
      setIngestUrl("");
      await loadFiles();
    } catch (err) {
      setError(err.message || "URL ingest failed");
    } finally {
      setIngesting(false);
    }
  }

  const readyCount = files.filter((f) => f.status === 2).length;
  const piiFiles = files.filter((f) => (f.pii_count || 0) > 0).length;
  const writeable = !workspaceReadOnly && writeableFromApi;
  const statusMeta = KB_STATUS_LABELS[kb?.status] || KB_STATUS_LABELS.empty;

  if (notFound) {
    return (
      <WorkspacePageShell user={user} loading={!user} maxWidth="max-w-5xl">
        <WorkspaceBackLink href="/knowledge">All libraries</WorkspaceBackLink>
        <div className="workspace-empty mt-10 rounded-[1.75rem] p-12 text-center">
          <p className="text-xl font-semibold">Library not found</p>
          <p className="mt-2 text-sm text-neutral-500">This knowledge base does not exist or you cannot access it.</p>
          <Link href="/knowledge" className="btn-primary mt-6 inline-flex">
            Back to libraries
          </Link>
        </div>
      </WorkspacePageShell>
    );
  }

  return (
    <WorkspacePageShell user={user} loading={!user || loading} loadingMessage="Loading library…" maxWidth="max-w-5xl">
      <WorkspaceBackLink href="/knowledge">All libraries</WorkspaceBackLink>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease }}
        className="workspace-hero rounded-[1.75rem] p-7 sm:p-9"
      >
        <div className="workspace-hero-glow pointer-events-none absolute inset-0" aria-hidden />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-4">
            <div className="workspace-icon-tile h-14 w-14 shrink-0">
              <KnowledgeIcon className="h-6 w-6" />
            </div>
            <div>
              <p className="workspace-section-label">Knowledge base</p>
              <h1 className="mt-1 font-serif text-3xl tracking-tight sm:text-4xl">{kb?.name}</h1>
              {kb?.description && (
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-neutral-500">{kb.description}</p>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                <span className={`rounded-full px-3 py-1 text-[11px] font-semibold ${statusMeta.color}`}>
                  {statusMeta.label}
                </span>
                {kb?.classification && (
                  <span className="rounded-full bg-violet-50 px-3 py-1 text-[11px] font-semibold text-violet-700 ring-1 ring-violet-200/60">
                    {kb.classification}
                  </span>
                )}
                <span className="rounded-full bg-white/70 px-3 py-1 text-[11px] font-semibold text-neutral-600 ring-1 ring-black/5">
                  {files.length} document{files.length !== 1 ? "s" : ""}
                </span>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200/60">
                  {readyCount} ready
                </span>
              </div>
            </div>
          </div>
          {writeable && (
            <div className="shrink-0">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.csv,.tsv,.xlsx,.pptx,.html,.htm,.json,.png,.jpg,.jpeg,.webp,.gif,.bmp,.tif,.tiff"
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
          <div className="relative mt-6 h-1.5 overflow-hidden rounded-full bg-neutral-200/80">
            <motion.div
              className="h-full bg-neutral-900"
              animate={{ width: `${uploadProgress}%` }}
              transition={{ ease: "linear" }}
            />
          </div>
        )}

        {error && <WorkspaceAlert type="error" className="relative mt-4">{error}</WorkspaceAlert>}

        <div className="relative mt-4 rounded-xl border border-neutral-200/70 bg-white/60 px-4 py-3 text-sm text-neutral-600">
          {piiFiles > 0
            ? `PII detected in ${piiFiles} file${piiFiles !== 1 ? "s" : ""} — previews are masked for confidential libraries.`
            : "Security scan: all indexed files clean (no PII patterns detected)."}
        </div>

        {writeable && (
          <form onSubmit={handleIngestUrl} className="relative mt-6 flex flex-col gap-3 sm:flex-row">
            <input
              type="url"
              value={ingestUrl}
              onChange={(e) => setIngestUrl(e.target.value)}
              placeholder="https://docs.example.com/page"
              className="input-field min-w-0 flex-1"
            />
            <button type="submit" disabled={ingesting || !ingestUrl.trim()} className="btn-primary shrink-0 disabled:opacity-50">
              {ingesting ? "Fetching…" : "Ingest URL"}
            </button>
          </form>
        )}
      </motion.div>

      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, ease }}
        className="mt-8"
      >
        <p className="workspace-section-label mb-4">Documents</p>

        {files.length === 0 ? (
          <div className="workspace-empty rounded-[1.75rem] p-10 text-center">
            <div className="workspace-icon-tile mx-auto h-12 w-12">
              <FileIcon className="h-5 w-5" />
            </div>
            <p className="mt-5 font-semibold">No documents yet</p>
            <p className="mt-2 text-sm text-neutral-500">
              Upload PDF, DOCX, CSV, XLSX, PPTX, HTML, JSON, Markdown, text, or images to index them for search.
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
                  className="workspace-list-row flex items-center gap-4 rounded-xl px-5 py-4"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-neutral-100 text-neutral-600">
                    <FileIcon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-neutral-900">{file.file_name}</p>
                    <p className="mt-0.5 text-[11px] text-neutral-400">
                      {file.update_time ? new Date(file.update_time).toLocaleString() : "—"}
                    </p>
                    {file.pii_count > 0 && (
                      <p className="mt-1 text-[11px] font-semibold text-amber-700">
                        PII detected ({file.pii_count})
                      </p>
                    )}
                    {file.status === 3 && file.error_message ? (
                      <p className="mt-1 line-clamp-2 text-[11px] text-red-600">{file.error_message}</p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {writeable && file.status === 3 ? (
                      <button
                        type="button"
                        onClick={() => handleRetry(file)}
                        className="rounded-full border border-neutral-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-neutral-700 hover:bg-neutral-50"
                      >
                        Retry
                      </button>
                    ) : null}
                    {writeable && file.id ? (
                      <button
                        type="button"
                        disabled={deletingId === file.id}
                        onClick={() => handleDelete(file)}
                        className="rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-[10px] font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50"
                      >
                        {deletingId === file.id ? "…" : "Delete"}
                      </button>
                    ) : null}
                    <span
                      className={`rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-wide uppercase ${status.color}`}
                    >
                      {status.label}
                    </span>
                  </div>
                </motion.li>
              );
            })}
          </ul>
        )}
      </motion.section>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, ease }}
        className="mt-8"
      >
        <KnowledgeQAPreview knowledgeId={knowledgeId} readyCount={readyCount} />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18, ease }}
        className="mt-8"
      >
        <button
          type="button"
          onClick={() => setAdvancedOpen((v) => !v)}
          className="flex w-full items-center justify-between rounded-2xl border border-neutral-200/80 bg-white/70 px-5 py-4 text-left text-sm font-semibold text-neutral-800"
        >
          <span>Optional: connectors & entity graph</span>
          <span className="text-neutral-400">{advancedOpen ? "▲" : "▼"}</span>
        </button>
        {advancedOpen && (
          <div className="mt-4 space-y-6">
            <KnowledgeSyncPanel collectionId={knowledgeId} writeable={writeable} />
            <KnowledgeGraphPanel files={files} writeable={writeable} />
          </div>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="workspace-panel mt-8 rounded-[1.75rem] p-6 text-sm"
      >
        <p className="font-semibold text-neutral-900">How it works</p>
        <ol className="mt-3 list-inside list-decimal space-y-2 text-[13px] leading-relaxed text-neutral-500">
          <li>Upload documents — they are chunked and indexed automatically (embeddings optional).</li>
          <li>Status turns <span className="font-semibold text-emerald-700">Ready</span> when indexing completes.</li>
          <li>Use Retrieve to preview passages, then open chat with this library linked.</li>
        </ol>
        <Link
          href={`/chat?knowledge_id=${knowledgeId}`}
          className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-neutral-900 hover:underline"
        >
          Open chat with this library →
        </Link>
      </motion.div>
    </WorkspacePageShell>
  );
}
