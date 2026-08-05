"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import TiltCard from "@/components/TiltCard";
import { springTab } from "@/lib/motion/workspace";

const ease = [0.16, 1, 0.3, 1];

const FILTER_TABS = [
  { id: "all", label: "All modules" },
  { id: "converse", label: "Converse" },
  { id: "build", label: "Build" },
  { id: "automate", label: "Automate" },
  { id: "explore", label: "Explore" },
];

export const DASHBOARD_MODULES = [
  {
    href: "/chat",
    label: "Chat",
    desc: "Stream responses with your AI assistants",
    category: "converse",
    featured: true,
    accent: "from-neutral-900 to-neutral-600",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
      </svg>
    ),
  },
  {
    href: "/knowledge",
    label: "Knowledge",
    desc: "Upload docs and power RAG answers",
    category: "build",
    accent: "from-stone-800 to-stone-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    ),
  },
  {
    href: "/model-lab",
    label: "Model Lab",
    desc: "Knowledge → train → auto-eval pipelines",
    category: "build",
    accent: "from-indigo-800 to-indigo-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        <circle cx="12" cy="12" r="4" />
      </svg>
    ),
  },
  {
    href: "/projects",
    label: "Projects",
    desc: "Hubs, workflows, and chat assistants",
    category: "build",
    featured: true,
    accent: "from-sky-800 to-sky-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M3 7h18M3 12h18M3 17h12" />
        <rect x="3" y="3" width="18" height="18" rx="2" />
      </svg>
    ),
  },
  {
    href: "/workflows",
    label: "Workflows",
    desc: "Automate multi-step AI pipelines visually",
    category: "automate",
    featured: true,
    accent: "from-emerald-800 to-emerald-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="6" cy="6" r="2.5" />
        <circle cx="18" cy="6" r="2.5" />
        <circle cx="12" cy="18" r="2.5" />
        <path d="M8 6h8M7.5 7.5L10.5 16M16.5 7.5L13.5 16" />
      </svg>
    ),
  },
  {
    href: "/runs",
    label: "Runs",
    desc: "Workflow execution history & logs",
    category: "automate",
    accent: "from-teal-800 to-teal-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 6h16M4 12h10M4 18h14" />
      </svg>
    ),
  },
  {
    href: "/credentials",
    label: "Credentials",
    desc: "API keys, Gmail, Telegram & secrets vault",
    category: "automate",
    accent: "from-cyan-800 to-cyan-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="8" cy="12" r="3" />
        <path d="M11 12h9M17 12v3M20 12v2" />
      </svg>
    ),
  },
  {
    href: "/marketplace",
    label: "Marketplace",
    desc: "Clone community workflows & templates",
    category: "explore",
    accent: "from-purple-700 to-purple-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
        <line x1="3" y1="6" x2="21" y2="6" />
        <path d="M16 10a4 4 0 0 1-8 0" />
      </svg>
    ),
  },
  {
    href: "/settings",
    label: "Settings",
    desc: "API health, models, and workspace config",
    category: "explore",
    accent: "from-neutral-700 to-neutral-400",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
      </svg>
    ),
  },
];

const CATEGORY_LABELS = {
  converse: "Converse",
  build: "Build",
  automate: "Automate",
  explore: "Explore",
};

function ModuleCard({ item, index }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.45, delay: index * 0.04, ease }}
    >
      <TiltCard className="h-full">
        <Link
          href={item.href}
          className="dashboard-module-card group relative flex h-full min-h-[148px] flex-col overflow-hidden rounded-2xl border border-white/60 bg-white/80 p-5 backdrop-blur-xl transition-all sm:p-6"
        >
          <div
            className={`pointer-events-none absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-500 group-hover:opacity-[0.06] ${item.accent}`}
          />
          <div className="relative flex items-start justify-between gap-3">
            <div className={`dashboard-module-icon bg-gradient-to-br ${item.accent} h-10 w-10`}>
              {item.icon}
            </div>
            <span className="rounded-full border border-black/6 bg-white/80 px-2 py-0.5 text-[9px] font-bold tracking-wider text-neutral-500 uppercase backdrop-blur-sm">
              {CATEGORY_LABELS[item.category]}
            </span>
          </div>
          <div className="relative mt-auto pt-4">
            <h3 className="text-base font-semibold tracking-tight text-neutral-900">{item.label}</h3>
            <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-neutral-500 sm:text-sm">{item.desc}</p>
            <p className="mt-3 flex items-center gap-1 text-xs font-semibold text-neutral-900 opacity-0 transition-all duration-300 group-hover:opacity-100">
              Open module
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </p>
          </div>
        </Link>
      </TiltCard>
    </motion.div>
  );
}

export default function DashboardModules() {
  const [activeFilter, setActiveFilter] = useState("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return DASHBOARD_MODULES.filter((m) => {
      const matchesCategory = activeFilter === "all" || m.category === activeFilter;
      const matchesQuery =
        !q ||
        m.label.toLowerCase().includes(q) ||
        m.desc.toLowerCase().includes(q) ||
        CATEGORY_LABELS[m.category].toLowerCase().includes(q);
      return matchesCategory && matchesQuery;
    });
  }, [activeFilter, query]);

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.22, duration: 0.6, ease }}
      className="dashboard-modules-section"
    >
      <div className="dashboard-modules-header">
        <div>
          <p className="workspace-section-label">Workspace modules</p>
          <h2 className="mt-1 font-serif text-2xl tracking-tight sm:text-3xl">
            Everything you need, <span className="text-gradient">one place</span>
          </h2>
          <p className="mt-2 max-w-xl text-sm text-neutral-500">
            Jump into chat, build knowledge, automate workflows — organized by how you work.
          </p>
        </div>
        <div className="dashboard-modules-search workspace-search-wrap mt-4 w-full sm:mt-0 sm:max-w-xs">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3-3" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search modules…"
            className="workspace-search-input"
            aria-label="Search modules"
          />
        </div>
      </div>

      <div className="mt-6 flex gap-2 overflow-x-auto pb-1">
        {FILTER_TABS.map((tab) => {
          const isActive = activeFilter === tab.id;
          const count =
            tab.id === "all"
              ? DASHBOARD_MODULES.length
              : DASHBOARD_MODULES.filter((m) => m.category === tab.id).length;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveFilter(tab.id)}
              className={`workspace-tab relative shrink-0 ${isActive ? "workspace-tab--active" : ""}`}
            >
              {isActive && (
                <motion.span
                  layoutId="dashboard-module-filter"
                  className="absolute inset-0 rounded-full bg-black shadow-lg"
                  transition={springTab}
                />
              )}
              <span className="relative z-10">
                {tab.label}
                <span className="workspace-tab-count ml-1">{count}</span>
              </span>
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="popLayout">
        {filtered.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="workspace-empty mt-6 rounded-2xl px-6 py-12 text-center"
          >
            <p className="font-medium text-neutral-900">No modules match your search</p>
            <p className="mt-1 text-sm text-neutral-500">Try a different filter or clear the search.</p>
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setActiveFilter("all");
              }}
              className="btn-secondary mt-4 text-sm"
            >
              Reset filters
            </button>
          </motion.div>
        ) : (
          <motion.div key={`${activeFilter}-${query}`} className="mt-6">
            <div className="dashboard-modules-bento">
              {filtered.map((item, i) => (
                <ModuleCard key={item.href} item={item} index={i} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
