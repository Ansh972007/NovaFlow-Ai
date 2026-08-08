"use client";

import { useMemo, useState } from "react";
import { NODE_ICONS } from "./WorkflowNodeIcons";

const BUILTIN_GROUPS = [
  { id: "triggers", label: "Triggers", types: ["trigger"] },
  { id: "logic", label: "Logic", types: ["condition", "loop", "parallel", "transform", "human", "subgraph"] },
  { id: "integrations", label: "Integrations", types: ["http", "notify", "jira", "github", "linear"] },
  { id: "ai", label: "AI & RAG", types: ["retrieve", "llm", "agent"] },
  { id: "output", label: "Output", types: ["output"] },
];

const MESSAGING_QUICK_NODES = [
  {
    type: "notify",
    label: "Telegram bot",
    subtitle: "Send Telegram message",
    iconKey: "telegram",
    preset: { channel: "telegram", label: "Telegram", to: "{{chat_id}}", message: "{{output}}" },
  },
  {
    type: "notify",
    label: "Send email",
    subtitle: "Gmail / SMTP",
    iconKey: "email",
    preset: { channel: "email", label: "Email", to: "{{email}}", subject: "NovaFlow", message: "{{output}}" },
  },
  {
    type: "notify",
    label: "Slack message",
    subtitle: "Post to Slack",
    iconKey: "slack",
    preset: { channel: "slack", label: "Slack", message: "{{output}}" },
  },
];

function NodeRow({ label, subtitle, iconKey, badge, onClick, disabled }) {
  const Icon = NODE_ICONS[iconKey] || NODE_ICONS.output;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-white/90 disabled:opacity-40"
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/80 text-neutral-600 ring-1 ring-black/[0.06]">
        <Icon size={14} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-semibold text-neutral-800">{label}</span>
        {subtitle ? (
          <span className="block truncate text-[10px] text-neutral-400">{subtitle}</span>
        ) : null}
      </span>
      {badge ? (
        <span className="shrink-0 rounded-full bg-amber-50 px-1.5 py-0.5 text-[9px] font-bold uppercase text-amber-700 ring-1 ring-amber-200/60">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

export default function NodeLibraryPanel({
  readOnly = false,
  builtinSchemas = [],
  dynamicComponents = [],
  customNodeDefs = [],
  onAddBuiltin,
  onAddComponent,
  onAddApiNode,
  onCreateApiNode,
  onImportOpenApi,
  fullHeight = false,
}) {
  const [query, setQuery] = useState("");

  const filteredBuiltin = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = builtinSchemas.length
      ? builtinSchemas
      : BUILTIN_GROUPS.flatMap((g) => g.types.map((type) => ({ type, label: type })));
    if (!q) return list;
    return list.filter(
      (s) =>
        (s.label || s.type || "").toLowerCase().includes(q) ||
        (s.type || "").toLowerCase().includes(q)
    );
  }, [builtinSchemas, query]);

  const filteredDynamic = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return dynamicComponents;
    return dynamicComponents.filter(
      (c) =>
        (c.label || c.name || "").toLowerCase().includes(q) ||
        (c.name || "").toLowerCase().includes(q)
    );
  }, [dynamicComponents, query]);

  const filteredCustom = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return customNodeDefs;
    return customNodeDefs.filter(
      (d) =>
        (d.display_name || d.slug || "").toLowerCase().includes(q) ||
        (d.slug || "").toLowerCase().includes(q)
    );
  }, [customNodeDefs, query]);

  return (
    <div
      className={`${fullHeight ? "flex h-full min-h-0 flex-col p-3" : "shrink-0 border-t border-black/[0.04] p-3"}`}
    >
      <p className="workspace-section-label mb-2">Node library</p>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search nodes…"
        className="input-field mb-2 w-full !py-1.5 !text-xs"
        disabled={readOnly}
      />
      <div
        className={`space-y-3 overflow-y-auto pr-1 ${
          fullHeight ? "min-h-0 flex-1" : "max-h-[280px]"
        }`}
      >
        {BUILTIN_GROUPS.map((group) => {
          const items = filteredBuiltin.filter((s) => group.types.includes(s.type));
          if (!items.length) return null;
          return (
            <div key={group.id}>
              <p className="sticky top-0 z-10 bg-white/90 py-1 text-[10px] font-bold uppercase tracking-wide text-neutral-400 backdrop-blur-sm">
                {group.label}
              </p>
              <ul className="space-y-0.5">
                {items.map((schema) => (
                  <li key={schema.type}>
                    <NodeRow
                      label={schema.label || schema.type}
                      subtitle={schema.type}
                      iconKey={schema.type}
                      onClick={() => onAddBuiltin?.(schema.type)}
                      disabled={readOnly}
                    />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}

        {!readOnly && MESSAGING_QUICK_NODES.some((n) => {
          const q = query.trim().toLowerCase();
          if (!q) return true;
          return (
            n.label.toLowerCase().includes(q) ||
            n.subtitle.toLowerCase().includes(q) ||
            n.type.toLowerCase().includes(q)
          );
        }) && (
          <div>
            <p className="sticky top-0 z-10 bg-white/90 py-1 text-[10px] font-bold uppercase tracking-wide text-neutral-400 backdrop-blur-sm">
              Messaging
            </p>
            <ul className="space-y-0.5">
              {MESSAGING_QUICK_NODES.filter((n) => {
                const q = query.trim().toLowerCase();
                if (!q) return true;
                return (
                  n.label.toLowerCase().includes(q) ||
                  n.subtitle.toLowerCase().includes(q) ||
                  n.type.toLowerCase().includes(q)
                );
              }).map((node) => (
                <li key={node.label}>
                  <NodeRow
                    label={node.label}
                    subtitle={node.subtitle}
                    iconKey={node.iconKey}
                    onClick={() => onAddBuiltin?.(node.type, node.preset)}
                    disabled={readOnly}
                  />
                </li>
              ))}
            </ul>
          </div>
        )}

        {filteredDynamic.length > 0 && (
          <div>
            <p className="sticky top-0 z-10 bg-white/90 py-1 text-[10px] font-bold uppercase tracking-wide text-sky-600 backdrop-blur-sm">
              AI components
            </p>
            <ul className="space-y-0.5">
              {filteredDynamic.map((comp) => (
                <li key={comp.name}>
                  <NodeRow
                    label={comp.label || comp.name}
                    subtitle={comp.name}
                    iconKey="component_node"
                    onClick={() => onAddComponent?.(comp)}
                    disabled={readOnly}
                  />
                </li>
              ))}
            </ul>
          </div>
        )}

        {(filteredCustom.length > 0 || !readOnly) && (
          <div>
            <p className="sticky top-0 z-10 bg-white/90 py-1 text-[10px] font-bold uppercase tracking-wide text-violet-600 backdrop-blur-sm">
              My API nodes
            </p>
            {filteredCustom.length === 0 ? (
              <p className="px-2 py-1 text-[10px] text-neutral-400">No custom nodes yet.</p>
            ) : (
              <ul className="space-y-0.5">
                {filteredCustom.map((def) => (
                  <li key={def.id}>
                    <NodeRow
                      label={def.display_name || def.slug}
                      subtitle={def.slug}
                      iconKey="api_node"
                      badge={def.status === "draft" ? "Draft" : null}
                      onClick={() => onAddApiNode?.(def)}
                      disabled={readOnly}
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {!readOnly && (
        <div className="mt-3 space-y-2 border-t border-black/[0.04] pt-3">
          <button
            type="button"
            onClick={onCreateApiNode}
            className="w-full rounded-lg border border-dashed border-violet-300 bg-violet-50/50 px-2 py-2 text-[10px] font-semibold text-violet-700 hover:bg-violet-50"
          >
            + Create API node
          </button>
          <button
            type="button"
            onClick={onImportOpenApi}
            className="w-full rounded-lg border border-dashed border-sky-300 bg-sky-50/50 px-2 py-2 text-[10px] font-semibold text-sky-700 hover:bg-sky-50"
          >
            Import OpenAPI spec
          </button>
        </div>
      )}
    </div>
  );
}
