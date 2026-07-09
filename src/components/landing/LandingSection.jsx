"use client";

import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

export default function LandingSection({
  children,
  className = "",
  delay = 0,
  id,
  as: Tag = "section",
}) {
  return (
    <Tag id={id} className={className}>
      <motion.div
        initial={{ opacity: 0, y: 48, filter: "blur(10px)" }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.85, delay, ease }}
      >
        {children}
      </motion.div>
    </Tag>
  );
}

export function LandingEyebrow({ children, delay = 0 }) {
  return (
    <motion.p
      initial={{ opacity: 0, letterSpacing: "0.35em" }}
      whileInView={{ opacity: 1, letterSpacing: "0.2em" }}
      viewport={{ once: true }}
      transition={{ duration: 0.8, delay, ease }}
      className="text-xs font-semibold tracking-[0.2em] text-muted uppercase"
    >
      {children}
    </motion.p>
  );
}

export function LandingTitle({ children, className = "", delay = 0.1 }) {
  return (
    <motion.h2
      initial={{ opacity: 0, y: 28, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.75, delay, ease }}
      className={`font-serif text-4xl tracking-tight sm:text-5xl ${className}`}
    >
      {children}
    </motion.h2>
  );
}
