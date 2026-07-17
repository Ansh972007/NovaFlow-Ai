"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

export default function DashboardPulse({ cards }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.18, ease }}
      className="dashboard-pulse-scroll -mx-1 flex gap-3 overflow-x-auto px-1 pb-1 sm:grid sm:grid-cols-2 sm:overflow-visible lg:grid-cols-5"
    >
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 + i * 0.05, ease }}
          whileHover={{ y: -3 }}
          className="min-w-[200px] shrink-0 sm:min-w-0"
        >
          <Link
            href={card.href}
            className="dashboard-pulse-card group block h-full rounded-2xl border border-white/55 bg-white/78 p-4 backdrop-blur-xl transition-all hover:border-black/10 hover:shadow-lg"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-[10px] font-semibold tracking-wide text-neutral-400 uppercase">{card.label}</p>
              <span className="text-neutral-300 transition-transform group-hover:translate-x-0.5 group-hover:text-neutral-500">
                →
              </span>
            </div>
            <p className="mt-2 text-lg font-semibold tracking-tight text-neutral-900">{card.value}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-neutral-500">{card.hint}</p>
            {card.extra && <p className="mt-1 text-[11px] text-neutral-400">{card.extra}</p>}
          </Link>
        </motion.div>
      ))}
    </motion.section>
  );
}
