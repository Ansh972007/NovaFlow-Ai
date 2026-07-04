"use client";

import Link from "next/link";
import Logo from "./Logo";

export default function AppHeader({ user, links = [] }) {
  const defaultLinks = [
    { href: "/", label: "Home" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/chat", label: "Chat" },
  ];

  const navLinks = links.length ? links : defaultLinks;

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo size="sm" />
        <div className="flex items-center gap-1 sm:gap-4">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-full px-3 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
          {user && (
            <span className="hidden rounded-full border border-border px-3 py-1.5 text-xs text-muted sm:inline">
              {user.user_name}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
