"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Logo from "./Logo";

const ease = [0.16, 1, 0.3, 1];

const linkGroups = [
  {
    title: "Product",
    links: [
      { href: "#features", label: "Features" },
      { href: "#pricing", label: "Pricing" },
      { href: "/chat", label: "Chat" },
      { href: "/dashboard", label: "Dashboard" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "#faq", label: "FAQ" },
      { href: "/docs", label: "Docs" },
      { href: "/login", label: "Sign in" },
      { href: "/login?mode=register", label: "Register" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="relative border-t border-border bg-white">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-black/25 to-transparent" />
      <motion.div
        initial={{ opacity: 0, scaleX: 0 }}
        whileInView={{ opacity: 1, scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.2, ease }}
        className="pointer-events-none absolute inset-x-12 top-0 h-px origin-center bg-gradient-to-r from-transparent via-black/40 to-transparent"
      />

      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-12 md:grid-cols-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.65, ease }}
            className="md:col-span-2"
          >
            <Logo size="sm" />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted">
              The professional AI workspace for teams who ship fast and think clearly.
            </p>
            <div className="mt-6 flex gap-3">
              {["X", "GitHub", "LinkedIn"].map((s, i) => (
                <motion.span
                  key={s}
                  whileHover={{ y: -3, scale: 1.06 }}
                  className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full border border-border text-xs font-medium text-muted transition-colors hover:border-foreground hover:text-foreground"
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 + i * 0.06, duration: 0.45, ease }}
                >
                  {s === "X" ? "𝕏" : s === "GitHub" ? "GH" : "in"}
                </motion.span>
              ))}
            </div>
          </motion.div>

          {linkGroups.map((group, gi) => (
            <motion.div
              key={group.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.08 + gi * 0.1, duration: 0.6, ease }}
            >
              <p className="text-xs font-semibold tracking-widest text-muted uppercase">{group.title}</p>
              <ul className="mt-4 space-y-3 text-sm text-muted">
                {group.links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href} className="group inline-flex items-center gap-1 transition-colors hover:text-foreground">
                      <span className="transition-transform duration-300 group-hover:translate-x-0.5">{link.label}</span>
                      <span className="opacity-0 transition-all duration-300 group-hover:opacity-100">→</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2, duration: 0.6, ease }}
          className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-border pt-8 sm:flex-row"
        >
          <p className="text-xs text-muted">© {new Date().getFullYear()} NovaFlow AI. All rights reserved.</p>
          <div className="flex gap-6 text-xs text-muted-light">
            {["Privacy", "Terms", "Status"].map((label) => (
              <span key={label} className="cursor-pointer transition-all hover:-translate-y-0.5 hover:text-foreground">
                {label}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </footer>
  );
}
