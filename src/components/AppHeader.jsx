"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import Logo from "./Logo";
import WorkspaceSwitcher from "./WorkspaceSwitcher";
import { logout } from "@/lib/api/auth";

export default function AppHeader({ user, links = [] }) {
  const router = useRouter();

  const defaultLinks = [
    { href: "/", label: "Home" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/chat", label: "Chat" },
    { href: "/knowledge", label: "Knowledge" },
    { href: "/apps", label: "Apps" },
    { href: "/workflows", label: "Workflows" },
    { href: "/agents", label: "Agents" },
    { href: "/marketplace", label: "Marketplace" },
    { href: "/evaluation", label: "Evaluation" },
  ];

  const navLinks = links.length ? links : defaultLinks;

  async function handleLogout() {
    try {
      await logout();
    } catch {
      /* clear local session even if API fails */
    }
    localStorage.removeItem("nf_token");
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-neutral-200/90 bg-white/95 backdrop-blur-xl shadow-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo size="sm" />
        <div className="flex items-center gap-1 sm:gap-2">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-full px-3 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
          {user ? (
            <>
              <WorkspaceSwitcher />
              <span className="hidden rounded-full border border-border px-3 py-1.5 text-xs text-muted lg:inline">
                {user.user_name}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-full px-3 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-foreground"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className="btn-primary !py-2 !text-sm">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
