"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

export default function WorkspaceEmpty({
  title,
  description,
  actionLabel,
  actionHref,
  onAction,
  icon = "○",
  className = "",
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12, filter: "blur(6px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.55, ease }}
      className={`workspace-empty rounded-2xl px-6 py-10 text-center ${className}`}
    >
      <motion.span
        animate={{ scale: [1, 1.06, 1], opacity: [0.5, 0.85, 0.5] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
        className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-black/10 bg-white text-lg font-serif text-neutral-400"
      >
        {icon}
      </motion.span>
      <p className="mt-4 text-sm font-semibold text-neutral-900">{title}</p>
      {description && <p className="mx-auto mt-1.5 max-w-sm text-sm text-neutral-500">{description}</p>}
      {actionLabel && actionHref && (
        <Link href={actionHref} className="btn-primary mt-5 inline-flex text-sm">
          {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && !actionHref && (
        <button type="button" onClick={onAction} className="btn-primary mt-5 inline-flex text-sm">
          {actionLabel}
        </button>
      )}
    </motion.div>
  );
}
