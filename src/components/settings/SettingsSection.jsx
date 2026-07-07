"use client";

import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

export default function SettingsSection({
  icon,
  title,
  description,
  actions,
  children,
  delay = 0,
  className = "",
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, ease }}
      className={`settings-section workspace-panel rounded-[1.75rem] p-6 sm:p-7 ${className}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 gap-4">
          {icon && <div className="settings-section-icon shrink-0">{icon}</div>}
          <div className="min-w-0">
            <h2 className="text-lg font-semibold tracking-tight text-neutral-900">{title}</h2>
            {description && (
              <p className="mt-1 text-sm leading-relaxed text-neutral-500">{description}</p>
            )}
          </div>
        </div>
        {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
      </div>
      {children && <div className="settings-section-body">{children}</div>}
    </motion.section>
  );
}

export function SettingsRow({ label, value, mono, border = true }) {
  return (
    <div
      className={`settings-kv-row flex justify-between gap-4 text-sm ${
        border ? "border-b border-black/[0.04] pb-3" : ""
      }`}
    >
      <dt className="shrink-0 text-neutral-500">{label}</dt>
      <dd className={`min-w-0 text-right font-medium text-neutral-800 ${mono ? "font-mono text-xs" : ""}`}>
        {value}
      </dd>
    </div>
  );
}

export function SettingsListItem({ children, active, className = "" }) {
  return (
    <li
      className={`settings-list-item workspace-list-row flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3 ${
        active ? "settings-list-item--active" : ""
      } ${className}`}
    >
      {children}
    </li>
  );
}

export function SettingsEmpty({ children }) {
  return (
    <div className="settings-empty workspace-empty mt-4 rounded-xl px-4 py-8 text-center text-sm text-neutral-500">
      {children}
    </div>
  );
}

export function SettingsMessage({ type = "info", children }) {
  if (!children) return null;
  const styles =
    type === "success"
      ? "border-emerald-200/80 bg-emerald-50/80 text-emerald-800"
      : type === "error"
        ? "border-red-200/80 bg-red-50/80 text-red-800"
        : type === "warn"
          ? "border-amber-200/80 bg-amber-50/80 text-amber-900"
          : "border-neutral-200/80 bg-neutral-50/80 text-neutral-700";
  return <p className={`settings-message mt-4 rounded-xl border px-3.5 py-2.5 text-sm ${styles}`}>{children}</p>;
}
