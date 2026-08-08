"use client";

import { useState } from "react";

function CheckIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M5 12.5 9.5 17 19 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

export default function CopyUriBox({ label, uri, className = "" }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!uri) return;
    try {
      await navigator.clipboard.writeText(uri);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className={className}>
      {label ? (
        <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-700">{label}</p>
      ) : null}
      <div
        className={`mt-1 flex items-center gap-2 rounded-lg border bg-white p-2 ring-1 transition ${
          copied ? "border-emerald-300 ring-emerald-100" : "border-sky-200/80 ring-sky-100"
        }`}
      >
        <code className="min-w-0 flex-1 break-all font-mono text-[11px] leading-relaxed text-neutral-700">
          {uri}
        </code>
        <button
          type="button"
          onClick={handleCopy}
          title={copied ? "Copied" : "Copy URI"}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition ${
            copied
              ? "border-emerald-300 bg-emerald-50 text-emerald-700"
              : "border-neutral-200 bg-neutral-50 text-neutral-600 hover:border-neutral-300 hover:bg-white"
          }`}
        >
          {copied ? <CheckIcon /> : <CopyIcon />}
        </button>
      </div>
      {copied ? (
        <p className="mt-1 text-[10px] font-medium text-emerald-700">Copied to clipboard</p>
      ) : null}
    </div>
  );
}
