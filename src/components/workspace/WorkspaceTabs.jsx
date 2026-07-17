"use client";

import { motion } from "framer-motion";
import { springTab } from "@/lib/motion/workspace";

export default function WorkspaceTabs({ tabs, active, onChange, className = "" }) {
  return (
    <div className={`workspace-tabs-scroll flex gap-2 overflow-x-auto pb-1 ${className}`}>
      {tabs.map((tab) => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`workspace-tab relative shrink-0 ${isActive ? "workspace-tab--active" : ""}`}
          >
            {isActive && (
              <motion.span
                layoutId="workspace-tab-pill"
                className="absolute inset-0 rounded-full bg-black shadow-lg"
                transition={springTab}
              />
            )}
            <span className="relative z-10 inline-flex items-center gap-1.5">
              {tab.icon && <span className="workspace-tab-icon">{tab.icon}</span>}
              {tab.label}
              {tab.count != null && <span className="workspace-tab-count">{tab.count}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function WorkspaceStatCard({ label, value, hint, status, index = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.6, delay: index * 0.07, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -4, scale: 1.01 }}
      className="workspace-stat workspace-stat-card group relative overflow-hidden rounded-2xl p-5"
    >
      <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100 nf-stat-shimmer" />
      <p className="workspace-section-label">{label}</p>
      <div className="relative mt-2 flex items-center gap-2">
        {status === "online" && <span className="settings-status-dot settings-status-dot--online" />}
        {status === "offline" && <span className="settings-status-dot settings-status-dot--offline" />}
        <p className="text-2xl font-semibold tracking-tight text-neutral-900">{value}</p>
      </div>
      {hint && <p className="relative mt-1.5 text-xs text-neutral-500">{hint}</p>}
    </motion.div>
  );
}

export function WorkspaceSkeletonList({ count = 3, height = "h-24" }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`workspace-panel nf-skeleton-shimmer ${height} rounded-2xl`}
          style={{ animationDelay: `${i * 0.12}s` }}
        />
      ))}
    </div>
  );
}

export function WorkspaceSkeletonGrid({ count = 3, columns = "sm:grid-cols-2 lg:grid-cols-3" }) {
  return (
    <div className={`grid gap-4 ${columns}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="workspace-panel nf-skeleton-shimmer h-44 rounded-2xl"
          style={{ animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  );
}
