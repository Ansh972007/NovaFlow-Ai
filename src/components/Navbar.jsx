"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import Logo from "./Logo";
import { useNavbarScroll } from "./ScrollProgress";

const links = [
  { href: "#features", label: "Features" },
  { href: "#bento", label: "Platform" },
  { href: "#pricing", label: "Pricing" },
  { href: "#testimonials", label: "Stories" },
];

export default function Navbar() {
  const scrolled = useNavbarScroll();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      <motion.header
        initial={{ y: -20, opacity: 0, filter: "blur(8px)" }}
        animate={{ y: 0, opacity: 1, filter: "blur(0px)" }}
        transition={{ duration: 0.75, ease: [0.16, 1, 0.3, 1] }}
        className={`fixed inset-x-0 top-0 z-50 transition-all duration-500 ${
          scrolled || menuOpen
            ? "border-b border-border/80 bg-white/90 shadow-[0_8px_30px_rgba(0,0,0,0.04)] backdrop-blur-xl"
            : "bg-transparent"
        }`}
      >
        <div className="mx-auto flex h-[4.25rem] max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo size="sm" />
          <nav className="hidden items-center gap-1 md:flex">
            {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="group relative rounded-full px-4 py-2 text-sm text-muted transition-all duration-300 hover:bg-white/80 hover:text-foreground hover:shadow-sm"
            >
              {link.label}
              <span className="absolute bottom-1 left-1/2 h-0.5 w-0 -translate-x-1/2 rounded-full bg-black transition-all duration-300 group-hover:w-1/2" />
            </Link>
            ))}
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              href="/login"
              className="hidden rounded-full px-4 py-2 text-sm font-medium text-muted transition-colors hover:text-foreground sm:inline"
            >
              Sign in
            </Link>
            <Link href="/login?mode=register" className="btn-primary !py-2.5 !px-5 text-sm">
              Get started
            </Link>
            <button
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              className="relative ml-1 flex h-10 w-10 items-center justify-center rounded-full border border-border md:hidden"
              aria-label="Toggle menu"
            >
              <span className={`block h-0.5 w-4 bg-foreground transition-all ${menuOpen ? "translate-y-0.5 rotate-45" : "-translate-y-1"}`} />
              <span className={`absolute block h-0.5 w-4 bg-foreground transition-all ${menuOpen ? "opacity-0" : ""}`} />
              <span className={`block h-0.5 w-4 bg-foreground transition-all ${menuOpen ? "-translate-y-0.5 -rotate-45" : "translate-y-1"}`} />
            </button>
          </div>
        </div>
      </motion.header>

      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-x-0 top-[4.25rem] z-40 border-b border-border bg-white/95 px-4 py-6 backdrop-blur-xl md:hidden"
          >
            <nav className="flex flex-col gap-1">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="rounded-xl px-4 py-3 text-lg font-medium transition-colors hover:bg-surface"
                >
                  {link.label}
                </Link>
              ))}
              <Link
                href="/login"
                onClick={() => setMenuOpen(false)}
                className="mt-2 rounded-xl px-4 py-3 text-lg text-muted"
              >
                Sign in
              </Link>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
