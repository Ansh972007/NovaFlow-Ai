"use client";

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { uploadConversationAttachment } from "@/lib/api/conversations";
import { classifyVoiceCommand, startVoiceInput } from "@/lib/chat/voiceInput";
import { polishVoiceTranscript } from "@/lib/chat/voicePolish";

/** Matches backend MAX_CHAT_UPLOAD_BYTES default (2 GiB). */
const MAX_CHAT_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024;

function formatBytes(n) {
  const v = Number(n) || 0;
  if (v < 1024) return `${v} B`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
  if (v < 1024 * 1024 * 1024) return `${(v / (1024 * 1024)).toFixed(1)} MB`;
  return `${(v / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default function ChatInput({
  onSend,
  onStop,
  disabled,
  streaming,
  ensureConversation,
  composerPending = false,
  onVoiceCommand,
}) {
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const voiceCtrlRef = useRef(null);
  const baseTextRef = useRef("");
  const interimRef = useRef("");

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadingLabel, setUploadingLabel] = useState("");
  const [uploadQueueInfo, setUploadQueueInfo] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const [listening, setListening] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("");
  const [voiceError, setVoiceError] = useState("");
  const [heardPreview, setHeardPreview] = useState("");

  const pendingAttachmentIds = pendingAttachments.map((a) => a.attachment_id).filter(Boolean);

  useEffect(() => {
    return () => {
      try {
        voiceCtrlRef.current?.stop?.();
      } catch {
        /* ignore */
      }
      voiceCtrlRef.current = null;
    };
  }, []);

  useEffect(() => {
    function onHotkey(e) {
      if (!(e.altKey && (e.key === "v" || e.key === "V"))) return;
      e.preventDefault();
      const btn = document.querySelector(
        '[aria-label="Start voice input"], [aria-label="Stop voice input"]',
      );
      btn?.click();
    }
    window.addEventListener("keydown", onHotkey);
    return () => window.removeEventListener("keydown", onHotkey);
  }, []);

  function syncComposerValue(finalText, interim = "") {
    const el = inputRef.current;
    if (!el) return;
    const next = `${finalText}${interim ? (finalText && !finalText.endsWith(" ") ? " " : "") + interim : ""}`;
    el.value = next;
    autoResize();
  }

  function appendFinalTranscript(chunk) {
    const raw = String(chunk || "").trim();
    if (!raw) return;
    const piece = polishVoiceTranscript(raw) || raw;
    if (!piece) return;

    const cmd = classifyVoiceCommand(piece);
    if (cmd && onVoiceCommand) {
      const handled = onVoiceCommand(cmd);
      if (handled !== false) {
        interimRef.current = "";
        setHeardPreview("");
        syncComposerValue(baseTextRef.current, "");
        return;
      }
    }

    const prev = baseTextRef.current.trim();
    baseTextRef.current = prev ? `${prev} ${piece}` : piece;
    interimRef.current = "";
    setHeardPreview(baseTextRef.current);
    syncComposerValue(baseTextRef.current, "");
  }

  async function stopVoice() {
    const ctrl = voiceCtrlRef.current;
    voiceCtrlRef.current = null;
    setListening(false);
    if (ctrl?.stop) {
      await ctrl.stop();
    }
    interimRef.current = "";
    syncComposerValue(baseTextRef.current, "");
    setVoiceStatus("");
  }

  function startVoice() {
    if (disabled || streaming || uploading) return;
    setVoiceError("");
    baseTextRef.current = (inputRef.current?.value || "").trim();
    interimRef.current = "";
    setListening(true);
    setVoiceStatus("listening");

    const ctrl = startVoiceInput({
      onPartial: (text) => {
        interimRef.current = text || "";
        syncComposerValue(baseTextRef.current, interimRef.current);
      },
      onFinal: (text) => {
        appendFinalTranscript(text);
      },
      onStatus: (s) => setVoiceStatus(s || ""),
      onError: (err) => {
        setVoiceError(err?.message || "Voice input failed");
        setListening(false);
        setVoiceStatus("");
        voiceCtrlRef.current = null;
      },
    });

    if (!ctrl) {
      setListening(false);
      setVoiceStatus("");
      setVoiceError("Voice input is not available in this browser.");
      return;
    }
    voiceCtrlRef.current = ctrl;
  }

  function toggleVoice() {
    if (listening) stopVoice();
    else startVoice();
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (listening) {
      stopVoice();
    }
    const value = inputRef.current?.value?.trim();
    if (!value) return;
    if (pendingAttachmentIds.length > 0) {
      onSend(value, {
        attachmentIds: pendingAttachmentIds,
        attachments: pendingAttachments.map((a) => ({
          file_name: a.file_name || a.name || "attachment",
          name: a.file_name || a.name || "attachment",
        })),
      });
    } else {
      onSend(value);
    }
    if (inputRef.current) {
      inputRef.current.value = "";
      inputRef.current.style.height = "auto";
    }
    baseTextRef.current = "";
    interimRef.current = "";
    setPendingAttachments([]);
    setUploadProgress(0);
    setUploadError("");
    setHeardPreview("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function autoResize() {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    if (!ensureConversation) {
      setUploadError("Cannot upload: chat is not ready yet.");
      return;
    }

    const oversize = files.filter((f) => (f.size || 0) > MAX_CHAT_UPLOAD_BYTES);
    if (oversize.length) {
      setUploadError(
        `File exceeds 2 GB limit: ${oversize.map((f) => f.name).join(", ")}. Use Knowledge for larger corpora.`,
      );
      return;
    }

    setUploadError("");
    setUploading(true);
    setUploadProgress(0);
    const nextPending = [...pendingAttachments];

    try {
      const conversationId = (await ensureConversation()) || "";
      if (!conversationId) throw new Error("No conversation id available");

      for (let i = 0; i < files.length; i += 1) {
        const file = files[i];
        setUploadingLabel(file.name || "file");
        setUploadQueueInfo(`${i + 1} of ${files.length} · ${formatBytes(file.size)}`);
        setUploadProgress(0);
        const res = await uploadConversationAttachment(conversationId, file, (pe) => {
          if (!pe) return;
          setUploadProgress(pe.percentage ?? 0);
        });

        nextPending.push({
          attachment_id: res.attachment_id,
          file_name: res.file_name,
          mime_type: res.mime_type,
          size_bytes: res.size_bytes,
          has_extracted_text: res.has_extracted_text,
          preview_text: res.preview_text,
          indexing_status: res.indexing_status || (res.has_extracted_text ? "extracted" : "ready"),
        });
        setPendingAttachments([...nextPending]);
      }
    } catch (err) {
      setUploadError(err?.message || "Upload failed");
    } finally {
      setUploading(false);
      setUploadingLabel("");
      setUploadQueueInfo("");
      setTimeout(() => setUploadProgress(0), 600);
    }
  }

  const placeholder = listening
    ? "Listening… speak now (click mic or Alt+V to stop)"
    : composerPending
      ? "Reply to refine, or use Approve / Test / Deploy on the card"
      : "Message your assistant…";

  const hasPendingIndex = pendingAttachments.some((a) => a.indexing_status === "pending");

  return (
    <div
      className="chat-composer-bar shrink-0 border-t border-neutral-200/60 bg-white/70 px-4 py-4 backdrop-blur-xl sm:px-6 sm:py-5"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (disabled || streaming) return;
        if (e.dataTransfer?.files?.length) handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.tsv,.json,.png,.jpg,.jpeg,.webp,.gif"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />

      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        onSubmit={handleSubmit}
        className="mx-auto max-w-3xl"
      >
        {pendingAttachments.length > 0 && (
          <div className="mb-3 rounded-xl border border-indigo-200/80 bg-indigo-50/60 p-3 text-xs text-indigo-900">
            <p className="font-semibold">Attachments ({pendingAttachments.length})</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {pendingAttachments.map((a, idx) => (
                <span
                  key={`${a.attachment_id || a.file_name || a.name}-${idx}`}
                  className="inline-flex max-w-[16rem] items-center gap-1 truncate rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] font-medium"
                  title={a.file_name || a.name}
                >
                  {a.file_name || a.name}
                  {a.size_bytes != null ? (
                    <span className="text-indigo-600/80">· {formatBytes(a.size_bytes)}</span>
                  ) : null}
                  {a.indexing_status === "pending" ? (
                    <span className="text-amber-700">· indexing…</span>
                  ) : null}
                </span>
              ))}
            </div>
            {hasPendingIndex && (
              <p className="mt-2 text-[10px] text-indigo-800/80">
                Large files extract in the background. Say &quot;index attachments&quot; to add them to Knowledge.
              </p>
            )}
          </div>
        )}

        {uploading && (
          <div className="mb-3 rounded-xl border border-neutral-200 bg-white/70 p-3 text-xs text-neutral-700">
            <div className="flex items-center justify-between gap-3">
              <span>
                Uploading: <span className="font-semibold">{uploadingLabel || "file"}</span>
                {uploadQueueInfo ? (
                  <span className="ml-1 text-neutral-500">({uploadQueueInfo})</span>
                ) : null}
              </span>
              <span className="font-semibold">{uploadProgress}%</span>
            </div>
            <div className="mt-2 h-2 w-full rounded-full bg-neutral-100">
              <div
                className="h-2 rounded-full bg-indigo-500"
                style={{ width: `${Math.max(0, Math.min(100, uploadProgress || 0))}%` }}
              />
            </div>
          </div>
        )}

        {(uploadError || voiceError) && (
          <div className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-[11px] text-red-800">
            {uploadError || voiceError}
          </div>
        )}

        {listening && (
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50/80 px-3 py-2 text-[11px] font-medium text-emerald-900">
            <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-emerald-600" />
            {voiceStatus === "processing" ? "Processing speech…" : "Listening — speak clearly"}
          </div>
        )}

        {!listening && heardPreview && (
          <div className="mb-3 rounded-xl border border-emerald-200/80 bg-emerald-50/50 px-3 py-2 text-[11px] text-emerald-950">
            <span className="font-semibold">Heard: </span>
            <span className="text-emerald-900">{heardPreview}</span>
            <span className="ml-2 text-emerald-700/80">Edit above if needed, then send.</span>
          </div>
        )}

        <div className="chat-composer-wrap">
          <div className="chat-composer flex items-end gap-2 p-2 pl-4">
            <motion.button
              type="button"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={openFilePicker}
              disabled={disabled || streaming || uploading || listening}
              className="mb-1 shrink-0 rounded-full border border-neutral-300 bg-white px-3 py-2 text-xs font-semibold text-neutral-700 shadow-sm hover:bg-neutral-50 disabled:opacity-40"
              aria-label="Attach file"
              title="Attach file (up to 2 GB each, chunked)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25">
                <path d="M21.44 11.05l-9.19 9.19a5.5 5.5 0 0 1-7.78-7.78l9.19-9.19a3.5 3.5 0 0 1 4.95 4.95l-9.2 9.19a1.5 1.5 0 1 1-2.12-2.12l8.49-8.48" />
              </svg>
            </motion.button>

            <motion.button
              type="button"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={toggleVoice}
              disabled={disabled || streaming || uploading}
              className={`mb-1 shrink-0 rounded-full border px-3 py-2 text-xs font-semibold shadow-sm disabled:opacity-40 ${
                listening
                  ? "border-emerald-600 bg-emerald-600 text-white"
                  : "border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50"
              }`}
              aria-label={listening ? "Stop voice input" : "Start voice input"}
              title={listening ? "Stop (Alt+V)" : "Voice input (Alt+V)"}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25">
                <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z" />
                <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
                <path d="M12 18v3" />
              </svg>
            </motion.button>

            <textarea
              ref={inputRef}
              rows={1}
              disabled={disabled && !streaming}
              onKeyDown={handleKeyDown}
              onInput={(e) => {
                baseTextRef.current = e.currentTarget.value;
                interimRef.current = "";
                autoResize();
              }}
              placeholder={placeholder}
              className="max-h-40 min-h-[48px] flex-1 resize-none bg-transparent py-3 text-sm leading-relaxed text-neutral-900 outline-none placeholder:text-neutral-400 disabled:opacity-50"
            />

            {streaming ? (
              <motion.button
                type="button"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={onStop}
                className="mb-1 shrink-0 rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-xs font-semibold text-neutral-700 shadow-sm hover:bg-neutral-50"
              >
                Stop
              </motion.button>
            ) : (
              <motion.button
                type="submit"
                disabled={disabled || uploading}
                whileHover={{ scale: disabled ? 1 : 1.05 }}
                whileTap={{ scale: disabled ? 1 : 0.95 }}
                className="chat-send-btn mb-1 shrink-0"
                aria-label="Send message"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </motion.button>
            )}
          </div>
        </div>
        <p className="mt-2.5 text-center text-[10px] font-medium tracking-wide text-neutral-400 uppercase">
          Enter to send · Shift+Enter new line · Alt+V voice · Attach up to 2 GB / file
        </p>
      </motion.form>
    </div>
  );
}
