"use client";

import VaultCredentialSelect from "./VaultCredentialSelect";

function fieldVisible(field, data) {
  const showWhen = field?.show_when;
  if (!showWhen) return true;
  for (const [k, v] of Object.entries(showWhen)) {
    if (k === "tools_contains") {
      const tools = data?.tools || [];
      const list = Array.isArray(tools) ? tools : String(tools).split(",").map((s) => s.trim());
      if (!list.includes(v)) return false;
    } else if (String(data?.[k] ?? "") !== String(v)) {
      return false;
    }
  }
  return true;
}

function labelWithRequired(field) {
  const base = field.label || field.key;
  return field.required ? `${base} *` : base;
}

export default function NodeSchemaFields({
  fields = [],
  data = {},
  onUpdate,
  readOnly = false,
  nodeType,
  knowledgeBases = [],
  workflows = [],
  customNodeDefs = [],
  currentWorkflowId = "",
}) {
  if (!fields?.length) return null;

  return (
    <>
      {fields.map((field) => {
        if (!fieldVisible(field, data)) return null;
        const key = field.key;
        const ft = field.field_type || "text";

        if (ft === "credential") {
          return (
            <VaultCredentialSelect
              key={key}
              nodeType={nodeType}
              nodeData={data}
              value={data[key] || ""}
              onChange={(v) => onUpdate({ [key]: v })}
              readOnly={readOnly}
              label={labelWithRequired(field)}
              vaultCategory={field.vault_category}
              vaultKind={field.vault_kind}
            />
          );
        }

        if (ft === "knowledge") {
          return (
            <label key={key} className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
              <select
                value={data[key] ?? ""}
                onChange={(e) =>
                  onUpdate({ [key]: e.target.value ? Number(e.target.value) : null })
                }
                disabled={readOnly}
                className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              >
                <option value="">Select knowledge base</option>
                {knowledgeBases.map((kb) => (
                  <option key={kb.id} value={kb.id}>{kb.name}</option>
                ))}
              </select>
            </label>
          );
        }

        if (ft === "workflow") {
          return (
            <label key={key} className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
              <select
                value={data[key] ?? ""}
                onChange={(e) => onUpdate({ [key]: e.target.value || null })}
                disabled={readOnly}
                className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              >
                <option value="">Select workflow</option>
                {workflows
                  .filter((w) => String(w.id) !== String(currentWorkflowId))
                  .map((w) => (
                    <option key={w.id} value={w.id}>{w.name || w.id}</option>
                  ))}
              </select>
            </label>
          );
        }

        if (ft === "node_def") {
          return (
            <label key={key} className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
              <select
                value={data[key] || ""}
                onChange={(e) => {
                  const def = customNodeDefs.find((d) => d.id === e.target.value);
                  onUpdate({
                    [key]: e.target.value,
                    label: def?.display_name || def?.slug || data.label || "",
                  });
                }}
                disabled={readOnly}
                className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              >
                <option value="">Select saved API node</option>
                {customNodeDefs.map((def) => (
                  <option key={def.id} value={def.id}>
                    {def.display_name || def.slug}
                  </option>
                ))}
              </select>
            </label>
          );
        }

        if (ft === "select") {
          return (
            <label key={key} className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
              <select
                value={data[key] ?? field.default ?? ""}
                onChange={(e) => onUpdate({ [key]: e.target.value })}
                disabled={readOnly}
                className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              >
                {(field.options || []).map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label || opt.value}</option>
                ))}
              </select>
            </label>
          );
        }

        if (ft === "checkbox") {
          return (
            <label key={key} className="mt-4 flex items-center gap-2 text-sm text-neutral-600">
              <input
                type="checkbox"
                checked={!!data[key]}
                onChange={(e) => onUpdate({ [key]: e.target.checked })}
                disabled={readOnly}
              />
              {labelWithRequired(field)}
            </label>
          );
        }

        if (ft === "textarea") {
          return (
            <label key={key} className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
              <textarea
                value={data[key] ?? field.default ?? ""}
                onChange={(e) => onUpdate({ [key]: e.target.value })}
                disabled={readOnly}
                rows={4}
                placeholder={field.placeholder || ""}
                className="mt-2 w-full resize-none rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              />
            </label>
          );
        }

        if (ft === "number") {
          return (
            <label key={key} className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
              <input
                type="number"
                value={data[key] ?? field.default ?? ""}
                onChange={(e) => onUpdate({ [key]: Number(e.target.value) })}
                disabled={readOnly}
                className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              />
            </label>
          );
        }

        if (key === "branches" || (ft === "text" && key === "tools")) {
          const arr = data[key];
          const str = Array.isArray(arr) ? arr.join(", ") : String(arr || field.default || "");
          return (
            <label key={key} className="mt-4 block">
              <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
              <input
                value={str}
                onChange={(e) =>
                  onUpdate({
                    [key]: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
                disabled={readOnly}
                placeholder={field.placeholder || ""}
                className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
              />
            </label>
          );
        }

        return (
          <label key={key} className="mt-4 block">
            <span className="text-xs font-semibold text-neutral-600">{labelWithRequired(field)}</span>
            <input
              value={data[key] ?? field.default ?? ""}
              onChange={(e) => onUpdate({ [key]: e.target.value })}
              disabled={readOnly}
              placeholder={field.placeholder || ""}
              className="mt-2 w-full rounded-xl border border-black/10 bg-white/90 px-3 py-2.5 text-sm"
            />
          </label>
        );
      })}
    </>
  );
}
