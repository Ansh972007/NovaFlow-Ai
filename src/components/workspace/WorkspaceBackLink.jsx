"use client";

import Link from "next/link";

export default function WorkspaceBackLink({ href, children }) {
  return (
    <Link
      href={href}
      className="workspace-back-link group mb-8 inline-flex items-center gap-2 text-sm font-medium text-neutral-500 transition-colors hover:text-neutral-900"
    >
      <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-neutral-200/80 bg-white/80 text-neutral-500 shadow-sm transition-all group-hover:-translate-x-0.5 group-hover:border-neutral-300 group-hover:text-neutral-900">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </span>
      {children}
    </Link>
  );
}
