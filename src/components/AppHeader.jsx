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
      { href: "/apps", label: "Apps" },
      { href: "/workflows", label: "Workflows" },
      { href: "/agents", label: "Agents" },
      { href: "/marketplace", label: "Marketplace" },
    ],
  },
  {
    label: "Quality",
    links: [{ href: "/evaluation", label: "Evaluation" }],
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
      compact ? "px-3 py-2 text-sm" : "px-3 py-2 text-[13px]",
      active
        ? "bg-neutral-900 text-white shadow-sm"
        : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
    ].join(" ");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-neutral-200/80 bg-white/90 backdrop-blur-xl supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex h-[4.25rem] max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <Logo size="sm" href={user ? "/dashboard" : "/"} className="shrink-0" />
          <span className="hidden h-5 w-px bg-neutral-200 lg:block" aria-hidden />
          <p className="hidden text-[11px] font-semibold tracking-[0.14em] text-neutral-400 uppercase lg:block">
            NovaFlow
          </p>
        </div>

        <nav className="hidden items-center gap-0.5 xl:flex" aria-label="Main">
          {useCustomLinks ? (
            links.map((link) => (
              <Link key={link.href} href={link.href} className={linkClass(link.href)}>
                {link.label}
              </Link>
            ))
          ) : (
            NAV_GROUPS.map((group, gi) => (
              <div key={group.label} className="flex items-center">
                {gi > 0 && <span className="mx-1.5 h-4 w-px bg-neutral-200" aria-hidden />}
                {group.links.map((link) => (
                  <Link key={link.href} href={link.href} className={linkClass(link.href)}>
                    {link.label}
                  </Link>
                ))}
              </div>
            ))
          )}
        </nav>

        <div className="flex items-center gap-1 sm:gap-2">
          {user && (
            <Link
              href="/settings"
              className={`hidden rounded-full p-2.5 transition-colors sm:inline-flex ${
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
              <span className="hidden max-w-[120px] truncate rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-700 lg:inline">
                {user.user_name}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className="hidden rounded-full px-3 py-2 text-sm text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900 sm:inline"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className="btn-primary !py-2 !text-sm">
              Sign in
            </Link>
          )}

          <button
            type="button"
            onClick={() => setMobileOpen((o) => !o)}
            className="inline-flex rounded-xl border border-neutral-200 bg-white p-2.5 text-neutral-700 shadow-sm xl:hidden"
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
