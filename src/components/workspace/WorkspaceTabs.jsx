"use client";

import { motion } from "framer-motion";

export default function WorkspaceTabs({ tabs, active, onChange, className = "" }) {
  return (
    <div className={`workspace-tabs-scroll flex gap-2 overflow-x-auto pb-1 ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`workspace-tab shrink-0 ${active === tab.id ? "workspace-tab--active" : ""}`}
        >
          {tab.icon && <span className="workspace-tab-icon">{tab.icon}</span>}
          {tab.label}
          {tab.count != null && (
            <span className="workspace-tab-count">{tab.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}

export function WorkspaceStatCard({ label, value, hint, status }) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.25 }}
      className="workspace-stat workspace-stat-card rounded-2xl p-5"
    >
      <p className="workspace-section-label">{label}</p>
      <div className="mt-2 flex items-center gap-2">
        {status === "online" && <span className="settings-status-dot settings-status-dot--online" />}
        {status === "offline" && <span className="settings-status-dot settings-status-dot--offline" />}
        <p className="text-2xl font-semibold tracking-tight text-neutral-900">{value}</p>
      </div>
      {hint && <p className="mt-1.5 text-xs text-neutral-500">{hint}</p>}
    </motion.div>
  );
}

export function WorkspaceSkeletonList({ count = 3, height = "h-24" }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`workspace-panel ${height} animate-pulse rounded-2xl`} />
      ))}
    </div>
  );
}

export function WorkspaceSkeletonGrid({ count = 3, columns = "sm:grid-cols-2 lg:grid-cols-3" }) {
  return (
    <div className={`grid gap-4 ${columns}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="workspace-panel h-44 animate-pulse rounded-2xl" />
      ))}
    </div>
  );
}
