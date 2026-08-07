"use client";

import { useState } from "react";
import { importOpenApiNodes } from "@/lib/api/workflows";

export default function OpenApiImportModal({ open, onClose, onImported }) {
  const [spec, setSpec] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  if (!open) return null;

  async function handleImport() {
    const raw = spec.trim();
    if (!raw) {
      setError("Paste an OpenAPI JSON spec");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await importOpenApiNodes(raw);
      setResult(res);
      onImported?.(res);
    } catch (err) {
      setError(err.message || "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Import OpenAPI</h2>
            <p className="mt-1 text-sm text-neutral-500">
              Bulk-create draft API nodes from an OpenAPI 3 JSON export.
            </p>
          </div>
          <button type="button" className="text-neutral-400 hover:text-neutral-700" onClick={onClose}>
            ✕
          </button>
        </div>

        <textarea
          className="input-field mt-4 w-full font-mono text-xs"
          rows={12}
          placeholder='{"openapi":"3.0.0","info":{"title":"My API"},...}'
          value={spec}
          onChange={(e) => setSpec(e.target.value)}
          disabled={busy}
        />

        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        {result && (
          <p className="mt-2 text-sm text-emerald-700">
            Imported {result.created?.length || 0} node(s) from {result.title || "spec"}.
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>
            Close
          </button>
          <button type="button" className="btn-primary" onClick={handleImport} disabled={busy}>
            {busy ? "Importing…" : "Import drafts"}
          </button>
        </div>
      </div>
    </div>
  );
}
