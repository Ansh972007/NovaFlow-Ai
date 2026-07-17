"use client";

import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

export default function WorkspaceHero({
  eyebrow,
  subtitle,
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
      initial={{ opacity: 0, y: 28, filter: "blur(8px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.75, ease }}
      className={`workspace-hero relative overflow-hidden rounded-[1.75rem] p-8 sm:p-10 ${className}`}
    >
      <div className="workspace-hero-glow nf-hero-glow-breathe pointer-events-none absolute inset-0" aria-hidden />
      <motion.div
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full border border-black/[0.04]"
        animate={{ rotate: 360 }}
        transition={{ duration: 50, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="pointer-events-none absolute -left-8 bottom-4 h-24 w-24 rounded-full bg-black/[0.02]"
        animate={{ y: [0, -8, 0], scale: [1, 1.05, 1] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          {badge && (
            <motion.div
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1, duration: 0.5, ease }}
              className="mb-4"
            >
              {badge}
            </motion.div>
          )}
          {eyebrow && (
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12, duration: 0.5, ease }}
              className="text-[11px] font-semibold tracking-[0.2em] text-neutral-400 uppercase"
            >
              {eyebrow}
            </motion.p>
          )}
          {subtitle && (
            <p className="mt-2 text-sm font-medium text-neutral-500">{subtitle}</p>
          )}
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18, duration: 0.65, ease }}
            className={`${subtitle ? "mt-1" : "mt-2"} font-serif text-4xl tracking-tight sm:text-[2.75rem]`}
          >
            {title}{" "}
            {titleHighlight && <span className="text-gradient">{titleHighlight}</span>}
          </motion.h1>
          {description && (
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.24, duration: 0.55, ease }}
              className="mt-3 max-w-lg text-[15px] leading-relaxed text-neutral-500"
            >
              {description}
            </motion.p>
          )}
        </div>
        {actions && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.28, duration: 0.5, ease }}
            className="flex shrink-0 flex-wrap gap-3"
          >
            {actions}
          </motion.div>
        )}
      </div>

      {children && <div className="relative mt-8 border-t border-black/[0.06] pt-8">{children}</div>}
    </motion.section>
  );
}
