"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { memo, useEffect, useState } from "react";
import { LayoutGroup, motion, AnimatePresence } from "framer-motion";
import Logo from "./Logo";
import WorkspaceSwitcher from "./WorkspaceSwitcher";
import NotificationBell from "./NotificationBell";
import { logout } from "@/lib/api/auth";
import { springTab } from "@/lib/motion/workspace";

const NAV_GROUPS = [
  {
    label: "Workspace",
    links: [
      {
        href: "/dashboard",
        label: "Dashboard",
        desc: "Overview of your workspace, stats, and key activities.",
        icon: (
          <svg className="h-5 w-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25A2.25 2.25 0 0 1 13.5 8.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
          </svg>
        )
      },
      {
        href: "/chat",
        label: "Chat",
        desc: "Interactive canvas to talk with models and run queries.",
        icon: (
          <svg className="h-5 w-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.083.205.13.431.13.669v.331c0 1.554-1.258 2.846-2.82 2.923-1.63.08-3.232.08-4.86 0-1.562-.077-2.82-1.369-2.82-2.923v-.331c0-.238.047-.464.13-.669a5.13 5.13 0 0 1 9.4 0ZM10.5 18.9h-3a3 3 0 0 1-3-3v-7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v2.25m-9 8.25h3c.162 0 .32-.015.474-.043a5.127 5.127 0 0 1-1.074-3.157v-.331" />
          </svg>
        )
      }
    ]
  },
  {
    label: "Build",
    links: [
      {
        href: "/knowledge",
        label: "Knowledge",
        desc: "Connect vector databases, files, and web links.",
        icon: (
          <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
          </svg>
        )
      },
      {
        href: "/workflows",
        label: "Workflows",
        desc: "Build automation pipelines with visual node editor.",
        icon: (
          <svg className="h-5 w-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
          </svg>
        )
      },
      {
        href: "/agents",
        label: "Agents",
        desc: "Create and program autonomous AI agents.",
        icon: (
          <svg className="h-5 w-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" />
          </svg>
        )
      },
      {
        href: "/model-lab",
        label: "Model Lab",
        desc: "Tune models and design system prompts.",
        icon: (
          <svg className="h-5 w-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.43l-1.003.828c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.43l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.991l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.645-.869l.214-1.28Z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
        )
      },
      {
        href: "/projects",
        label: "Projects",
        desc: "Organize files, templates, and evaluations.",
        icon: (
          <svg className="h-5 w-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-19.5 0A2.25 2.25 0 0 0 4.5 15h15a2.25 2.25 0 0 0 2.25-2.25m-19.5 0v.25A2.25 2.25 0 0 0 4.5 17.5h15a2.25 2.25 0 0 0 2.25-2.25v-.25m-19.5 0V9A2.25 2.25 0 0 1 4.5 6.75h5.06a2.25 2.25 0 0 1 1.683.76l1.246 1.494a2.25 2.25 0 0 0 1.683.76h5.328A2.25 2.25 0 0 1 21.75 12v.75m-19.5 0h19.5" />
          </svg>
        )
      },
      {
        href: "/apps",
        label: "Apps",
        desc: "Configure client interfaces and portals.",
        icon: (
          <svg className="h-5 w-5 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9 3 3m12 6V4.5M15 9h4.5M15 9l6-6m-6 12v4.5M15 15h4.5M15 15l6 6m-6-6v4.5M9 15H4.5M9 15l-6 6" />
          </svg>
        )
      },
      {
        href: "/runs",
        label: "Runs",
        desc: "Audit trace paths, execution metrics, and logs.",
        icon: (
          <svg className="h-5 w-5 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
        )
      },
      {
        href: "/digests",
        label: "Digests",
        desc: "View scheduled report summaries and briefs.",
        icon: (
          <svg className="h-5 w-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5A3.375 3.375 0 0 0 10.125 2.25H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
        )
      },
      {
        href: "/marketplace",
        label: "Marketplace",
        desc: "Import community workflows, agents, and prompts.",
        icon: (
          <svg className="h-5 w-5 text-pink-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 21v-7.5a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 .75.75V21m-4.5 0H2.36m11.14 0H18m0 0h3.64m-1.39 0V9.349M3.75 21V9.349m0 0a3.001 3.001 0 0 0 3.75-.615 3.001 3.001 0 0 0 5.485.06 3.001 3.001 0 0 0 5.485-.06 3.001 3.001 0 0 0 3.75.615m-18.5 0V4.875C1.25 4.116 1.866 3.5 2.625 3.5h18.75c.759 0 1.375.616 1.375 1.375V9.35" />
          </svg>
        )
      }
    ]
  },
  {
    label: "Quality",
    links: [
      {
        href: "/evaluation",
        label: "Evaluation",
        desc: "Benchmark performance models and tracking.",
        icon: (
          <svg className="h-5 w-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" />
          </svg>
        )
      },
      {
        href: "/developer",
        label: "Developer",
        desc: "Access API keys, webhooks, and integrations.",
        icon: (
          <svg className="h-5 w-5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
          </svg>
        )
      },
      {
        href: "/docs",
        label: "Docs",
        desc: "Explore API references, guides, and tutorials.",
        icon: (
          <svg className="h-5 w-5 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
          </svg>
        )
      }
    ]
  }
];

function isActive(pathname, href) {
  if (href === "/dashboard") return pathname === "/dashboard";
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({ href, label, pathname, compact = false }) {
  const active = isActive(pathname, href);
  return (
    <Link
      href={href}
      className={[
        "relative shrink-0 rounded-full font-medium transition-colors duration-200",
        compact ? "px-3 py-2 text-sm" : "px-2.5 py-1.5 text-[12px] sm:px-3 sm:py-2 sm:text-[13px]",
        active ? "text-white" : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
      ].join(" ")}
    >
      {active && (
        <motion.span
          layoutId="app-header-nav-pill"
          className="absolute inset-0 rounded-full bg-neutral-900 shadow-sm"
          transition={springTab}
        />
      )}
      <span className="relative z-10">{label}</span>
    </Link>
  );
}

function NavDropdown({ group, activeDropdown, setActiveDropdown, pathname }) {
  const isOpen = activeDropdown === group.label;

  return (
    <div
      className="relative"
      onMouseEnter={() => setActiveDropdown(group.label)}
      onMouseLeave={() => setActiveDropdown(null)}
    >
      <button
        type="button"
        className={[
          "relative flex items-center gap-1 rounded-full px-3.5 py-2 text-[13px] font-medium transition-all duration-200 outline-none",
          isOpen ? "text-neutral-900 bg-neutral-100/80" : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900",
        ].join(" ")}
      >
        <span>{group.label}</span>
        <svg
          className={[
            "h-3.5 w-3.5 transition-transform duration-200 text-neutral-400",
            isOpen ? "transform rotate-180 text-neutral-700" : "",
          ].join(" ")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className={[
              "absolute left-1/2 z-50 mt-2 -translate-x-1/2 rounded-2xl border border-neutral-200/80 bg-white/95 p-4 shadow-xl backdrop-blur-xl",
              group.label === "Build" ? "w-[580px]" : "w-[440px]"
            ].join(" ")}
          >
            <div className={[
              "grid gap-2",
              group.label === "Build" ? "grid-cols-2" : "grid-cols-1"
            ].join(" ")}>
              {group.links.map((link) => {
                const active = isActive(pathname, link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={[
                      "flex items-start gap-3.5 rounded-xl p-3 transition-all duration-200 border border-transparent",
                      active
                        ? "bg-neutral-900 text-white shadow-sm"
                        : "hover:bg-neutral-50 hover:border-neutral-100"
                    ].join(" ")}
                  >
                    <div className={[
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                      active ? "bg-white/10 text-white" : "bg-neutral-100 text-neutral-600"
                    ].join(" ")}>
                      {link.icon}
                    </div>
                    <div className="min-w-0">
                      <p className={[
                        "text-[13px] font-semibold leading-none",
                        active ? "text-white" : "text-neutral-900"
                      ].join(" ")}>
                        {link.label}
                      </p>
                      <p className={[
                        "mt-1.5 text-[11px] leading-normal",
                        active ? "text-neutral-200/85" : "text-neutral-500"
                      ].join(" ")}>
                        {link.desc}
                      </p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function AppHeader({ user, links = [] }) {
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState(null);

  const useCustomLinks = links.length > 0;

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  async function handleLogout() {
    try {
      await logout();
    } catch {
      try {
        localStorage.removeItem("nf_token");
        localStorage.removeItem("nf_refresh_token");
      } catch {
        /* ignore */
      }
    }
    router.push("/login");
  }

  return (
    <motion.header
      initial={{ y: -12, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="sticky top-0 z-40 border-b border-neutral-200/80 bg-white/90 backdrop-blur-xl supports-[backdrop-filter]:bg-white/80 w-full"
    >
      <div className="mx-auto flex h-16 w-full max-w-[1440px] items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6 min-w-0">
          <div className="flex shrink-0 items-center">
            <Logo size="sm" href={user ? "/dashboard" : "/"} />
          </div>

          <nav
            className="hidden lg:flex items-center gap-1 min-w-0"
            aria-label="Main"
          >
            {useCustomLinks ? (
              <LayoutGroup id="app-header-nav">
                <div className="flex max-w-full flex-nowrap items-center gap-0.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                  {links.map((link) => (
                    <NavLink key={link.href} href={link.href} label={link.label} pathname={pathname} />
                  ))}
                </div>
              </LayoutGroup>
            ) : (
              NAV_GROUPS.map((group) => (
                <NavDropdown
                  key={group.label}
                  group={group}
                  activeDropdown={activeDropdown}
                  setActiveDropdown={setActiveDropdown}
                  pathname={pathname}
                />
              ))
            )}
          </nav>
        </div>

        <div className="flex shrink-0 flex-nowrap items-center gap-1.5 sm:gap-2">
          {user && (
            <>
              <NotificationBell />
              <Link
                href="/settings"
                className={`hidden shrink-0 items-center rounded-full p-2 transition-colors sm:inline-flex ${
                  isActive(pathname, "/settings")
                    ? "bg-neutral-900 text-white"
                    : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
                }`}
                title="Settings"
                aria-label="Settings"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </svg>
              </Link>
            </>
          )}

          {user ? (
            <>
              <WorkspaceSwitcher />
              <button
                type="button"
                onClick={handleLogout}
                className="hidden shrink-0 whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900 sm:inline-flex sm:items-center"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className="btn-primary shrink-0 whitespace-nowrap !py-2 !text-sm">
              Sign in
            </Link>
          )}

          <button
            type="button"
            onClick={() => setMobileOpen((o) => !o)}
            className="inline-flex shrink-0 rounded-xl border border-neutral-200 bg-white p-2.5 text-neutral-700 shadow-sm lg:hidden"
            aria-expanded={mobileOpen}
            aria-label="Open menu"
          >
            {mobileOpen ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-neutral-200/80 bg-white/95 px-4 py-4 backdrop-blur-xl lg:hidden">
          <nav className="space-y-4" aria-label="Mobile">
            {useCustomLinks ? (
              <div className="flex flex-wrap gap-2">
                {links.map((link) => (
                  <NavLink key={link.href} href={link.href} label={link.label} pathname={pathname} compact />
                ))}
              </div>
            ) : (
              NAV_GROUPS.map((group) => (
                <div key={group.label}>
                  <p className="mb-2 text-[10px] font-bold tracking-[0.16em] text-neutral-400 uppercase">{group.label}</p>
                  <div className="flex flex-wrap gap-2">
                    {group.links.map((link) => (
                      <NavLink key={link.href} href={link.href} label={link.label} pathname={pathname} compact />
                    ))}
                  </div>
                </div>
              ))
            )}
            {user && (
              <div className="flex flex-wrap gap-2 border-t border-neutral-100 pt-4">
                <NavLink href="/settings" label="Settings" pathname={pathname} compact />
                <button
                  type="button"
                  onClick={handleLogout}
                  className="rounded-full px-3 py-2 text-sm text-neutral-500 hover:bg-neutral-100"
                >
                  Sign out
                </button>
              </div>
            )}
          </nav>
        </div>
      )}
    </motion.header>
  );
}

export default memo(AppHeader);
