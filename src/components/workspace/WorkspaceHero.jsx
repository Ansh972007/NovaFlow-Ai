"use client";

import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

export default function WorkspaceHero({
  eyebrow,
  title,
  titleHighlight,
  description,
  actions,
  badge,
  children,
  className = "",
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 22 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease }}
      className={`workspace-hero relative overflow-hidden rounded-[1.75rem] p-8 sm:p-10 ${className}`}
    >
      <div className="workspace-hero-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          {badge && <div className="mb-4">{badge}</div>}
          {eyebrow && (
            <p className="text-[11px] font-semibold tracking-[0.2em] text-neutral-400 uppercase">
              {eyebrow}
            </p>
          )}
          <h1 className="mt-2 font-serif text-4xl tracking-tight sm:text-[2.75rem]">
            {title}{" "}
            {titleHighlight && <span className="text-gradient">{titleHighlight}</span>}
          </h1>
          {description && (
            <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-neutral-500">{description}</p>
          )}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap gap-3">{actions}</div>}
      </div>

      {children && <div className="relative mt-8 border-t border-black/[0.06] pt-8">{children}</div>}
    </motion.section>
  );
}
