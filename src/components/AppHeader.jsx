"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { memo, useEffect, useState } from "react";
import Logo from "./Logo";
import WorkspaceSwitcher from "./WorkspaceSwitcher";
import { logout } from "@/lib/api/auth";

const NAV_GROUPS = [
  {
    label: "Workspace",
    links: [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/chat", label: "Chat" },
    ],
  },
  {
    label: "Build",
    links: [
      { href: "/knowledge", label: "Knowledge" },
      { href: "/model-lab", label: "Model Lab" },
      { href: "/projects", label: "Projects" },
      { href: "/apps", label: "Apps" },
      { href: "/workflows", label: "Workflows" },
      { href: "/runs", label: "Runs" },
      { href: "/digests", label: "Digests" },
      { href: "/agents", label: "Agents" },
      { href: "/marketplace", label: "Marketplace" },
    ],
  },
  {
    label: "Quality",
    links: [
      { href: "/evaluation", label: "Evaluation" },
      { href: "/developer", label: "Developer" },
      { href: "/docs", label: "Docs" },
    ],
  },
];

function isActive(pathname, href) {
  if (href === "/dashboard") return pathname === "/dashboard";
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function AppHeader({ user, links = [] }) {
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const useCustomLinks = links.length > 0;

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  async function handleLogout() {
    try {
      await logout();
    } catch {
      /* clear local session even if API fails */
    }
    localStorage.removeItem("nf_token");
    router.push("/login");
  }

  function linkClass(href, compact = false) {
    const active = isActive(pathname, href);
    return [
      "relative rounded-full font-medium transition-all duration-200",
      compact ? "px-3 py-2 text-sm" : "px-2.5 py-1.5 text-[12px] sm:px-3 sm:py-2 sm:text-[13px]",
      active
        ? "bg-neutral-900 text-white shadow-sm"
        : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
    ].join(" ");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-neutral-200/80 bg-white/90 backdrop-blur-xl supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex h-16 w-full max-w-[1440px] items-center gap-2 px-4 sm:gap-3 sm:px-6">
        <div className="flex shrink-0 items-center">
          <Logo size="sm" href={user ? "/dashboard" : "/"} />
        </div>

        <nav
          className="hidden min-w-0 flex-1 justify-center xl:flex"
          aria-label="Main"
        >
          <div className="flex max-w-full flex-nowrap items-center gap-0.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {useCustomLinks ? (
              links.map((link) => (
                <Link key={link.href} href={link.href} className={`${linkClass(link.href)} shrink-0`}>
                  {link.label}
                </Link>
              ))
            ) : (
              NAV_GROUPS.map((group, gi) => (
                <div key={group.label} className="flex shrink-0 items-center">
                  {gi > 0 && <span className="mx-1 h-4 w-px shrink-0 bg-neutral-200" aria-hidden />}
                  {group.links.map((link) => (
                    <Link key={link.href} href={link.href} className={`${linkClass(link.href)} shrink-0`}>
                      {link.label}
                    </Link>
                  ))}
                </div>
              ))
            )}
          </div>
        </nav>

        <div className="flex shrink-0 flex-nowrap items-center gap-1.5 sm:gap-2">
          {user && (
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
          )}

          {user ? (
            <>
              <WorkspaceSwitcher />
              <button
                type="button"
                onClick={handleLogout}
                className="hidden shrink-0 whitespace-nowrap rounded-full px-3 py-2 text-sm text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900 sm:inline-flex sm:items-center"
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
            className="inline-flex shrink-0 rounded-xl border border-neutral-200 bg-white p-2.5 text-neutral-700 shadow-sm xl:hidden"
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
        <div className="border-t border-neutral-200/80 bg-white/95 px-4 py-4 backdrop-blur-xl xl:hidden">
          <nav className="space-y-4" aria-label="Mobile">
            {useCustomLinks ? (
              <div className="flex flex-wrap gap-2">
                {links.map((link) => (
                  <Link key={link.href} href={link.href} className={linkClass(link.href, true)}>
                    {link.label}
                  </Link>
                ))}
              </div>
            ) : (
              NAV_GROUPS.map((group) => (
                <div key={group.label}>
                  <p className="mb-2 text-[10px] font-bold tracking-[0.16em] text-neutral-400 uppercase">{group.label}</p>
                  <div className="flex flex-wrap gap-2">
                    {group.links.map((link) => (
                      <Link key={link.href} href={link.href} className={linkClass(link.href, true)}>
                        {link.label}
                      </Link>
                    ))}
                  </div>
                </div>
              ))
            )}
            {user && (
              <div className="flex flex-wrap gap-2 border-t border-neutral-100 pt-4">
                <Link href="/settings" className={linkClass("/settings", true)}>
                  Settings
                </Link>
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
    </header>
  );
}

export default memo(AppHeader);
