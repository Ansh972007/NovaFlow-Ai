"use client";

import { useEffect, useState } from "react";
import { listLlmProviders } from "@/lib/api/llm";

export default function ChatPlanningSelector({ label, onSelectModel }) {
  const [providers, setProviders] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    listLlmProviders()
      .then((res) => {
        const rows = res?.providers || res?.data?.providers || res || [];
        setProviders(Array.isArray(rows) ? rows : []);
      })
      .catch(() => setProviders([]));
  }, []);

  const options = providers.flatMap((p) => {
    const models = p.models || p.model_list || [];
    return models.map((m) => ({
      id: `${p.id || p.name}-${m.model_name || m.id}`,
      label: `${p.name || p.server_name || "Provider"} · ${m.model_name || m.id}`,
      model: m.model_name || m.id,
      providerId: p.id,
    }));
  });

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-violet-200/80 bg-violet-50/90 px-2.5 py-0.5 text-[10px] font-semibold text-violet-800"
        title="Planning model for workflow compose"
      >
        <span className="truncate">{label || "Planning model"}</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 min-w-[240px] rounded-xl border border-neutral-200 bg-white p-2 shadow-lg">
          <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
            Compose / orchestrator model
          </p>
          <button
            type="button"
            className="w-full rounded-lg px-2 py-1.5 text-left text-xs hover:bg-neutral-50"
            onClick={() => {
              onSelectModel?.("use workspace default");
              setOpen(false);
            }}
          >
            Workspace default
          </button>
          {options.slice(0, 12).map((opt) => (
            <button
              key={opt.id}
              type="button"
              className="w-full rounded-lg px-2 py-1.5 text-left text-xs hover:bg-neutral-50"
              onClick={() => {
                onSelectModel?.(`use model ${opt.model}`);
                setOpen(false);
              }}
            >
              {opt.label}
            </button>
          ))}
          <button
            type="button"
            className="mt-1 w-full rounded-lg border border-dashed border-neutral-200 px-2 py-1.5 text-left text-xs text-neutral-600 hover:bg-neutral-50"
            onClick={() => {
              onSelectModel?.("List providers");
              setOpen(false);
            }}
          >
            List all providers
          </button>
        </div>
      )}
    </div>
  );
}
