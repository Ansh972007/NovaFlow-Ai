"use client";

import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

function BorderSvg({ type }) {
  const common = "pointer-events-none absolute inset-0 h-full w-full overflow-visible";
  const vb = "0 0 100 100";
  const stroke = "black";
  const rx = 14;

  if (type === "arc") {
    return (
      <svg className={common} preserveAspectRatio="none" viewBox={vb}>
        {[0, 1, 2, 3].map((c) => (
          <motion.path
            key={c}
            d={c === 0 ? "M10 2 H24" : c === 1 ? "M76 2 H90" : c === 2 ? "M2 76 V90" : "M98 76 V90"}
            fill="none"
            stroke={stroke}
            strokeWidth="1"
            strokeLinecap="round"
            animate={{ opacity: [0.12, 0.85, 0.12], pathLength: [0.25, 1, 0.25] }}
            transition={{ duration: 2, repeat: Infinity, delay: c * 0.2, ease: "easeInOut" }}
          />
        ))}
        <motion.rect
          x="2"
          y="2"
          width="96"
          height="96"
          rx={rx}
          fill="none"
          stroke={stroke}
          strokeWidth="0.6"
          strokeOpacity="0.15"
          animate={{ strokeOpacity: [0.1, 0.35, 0.1] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />
      </svg>
    );
  }

  if (type === "beam") {
    return (
      <>
        <svg className={common} preserveAspectRatio="none" viewBox={vb}>
          <rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.2" />
        </svg>
        <motion.div
          className="pointer-events-none absolute inset-x-8 top-0 h-px bg-black"
          animate={{ y: [0, 120, 0], opacity: [0, 0.55, 0] }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "linear" }}
        />
      </>
    );
  }

  if (type === "comet") {
    return (
      <>
        <svg className={common} preserveAspectRatio="none" viewBox={vb}>
          <rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.22" />
        </svg>
        <motion.div
          className="pointer-events-none absolute h-1 w-1 rounded-full bg-black"
          animate={{
            top: ["3%", "3%", "97%", "97%", "3%"],
            left: ["3%", "97%", "97%", "3%", "3%"],
            opacity: [0.15, 1, 1, 1, 0.15],
          }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
        />
      </>
    );
  }

  if (type === "tick") {
    return (
      <svg className={common} preserveAspectRatio="none" viewBox={vb}>
        <motion.rect
          x="2"
          y="2"
          width="96"
          height="96"
          rx={rx}
          fill="none"
          stroke={stroke}
          strokeWidth="1"
          pathLength="1"
          strokeDasharray="0.05 0.95"
          animate={{ strokeDashoffset: [0, -1] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "linear" }}
        />
      </svg>
    );
  }

  return (
    <svg className={common} preserveAspectRatio="none" viewBox={vb}>
      <motion.rect
        x="2"
        y="2"
        width="96"
        height="96"
        rx={rx}
        fill="none"
        stroke={stroke}
        strokeWidth="1"
        strokeDasharray="3 9"
        animate={{ strokeDashoffset: [0, -24] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
      />
    </svg>
  );
}

export default function LandingGodFrame({
  children,
  type = "needle",
  className = "",
  innerClassName = "",
  delay = 0,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.98 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.9, delay, ease }}
      className={`relative ${className}`}
    >
      <div className="pointer-events-none absolute -inset-px rounded-[1.35rem]">
        <BorderSvg type={type} />
      </div>
      <motion.div
        className={`relative overflow-hidden rounded-[1.3rem] border border-black/10 bg-white/90 shadow-[0_24px_80px_rgba(0,0,0,0.08)] backdrop-blur-xl ${innerClassName}`}
        whileHover={{ y: -4, boxShadow: "0 32px 90px rgba(0,0,0,0.12)" }}
        transition={{ duration: 0.45, ease }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

export function LandingSectionDivider() {
  return (
    <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
      <div className="relative h-px overflow-hidden bg-border/60">
        <motion.div
          className="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-black/40 to-transparent"
          animate={{ x: ["-100%", "400%"] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: "linear" }}
        />
      </div>
    </div>
  );
}

export function LandingOrbitRings({ className = "" }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      {[1, 2, 3].map((ring) => (
        <motion.div
          key={ring}
          className="absolute left-1/2 top-1/2 rounded-full border border-black/[0.06]"
          style={{
            width: `${ring * 28 + 40}%`,
            height: `${ring * 28 + 40}%`,
            marginLeft: `-${(ring * 28 + 40) / 2}%`,
            marginTop: `-${(ring * 28 + 40) / 2}%`,
          }}
          animate={{ rotate: ring % 2 === 0 ? 360 : -360, opacity: [0.15, 0.45, 0.15] }}
          transition={{
            rotate: { duration: 40 + ring * 15, repeat: Infinity, ease: "linear" },
            opacity: { duration: 5 + ring, repeat: Infinity, ease: "easeInOut" },
          }}
        />
      ))}
      {[...Array(8)].map((_, i) => (
        <motion.span
          key={i}
          className="absolute h-0.5 w-0.5 rounded-full bg-black/30"
          style={{
            left: `${12 + i * 11}%`,
            top: `${18 + (i % 4) * 18}%`,
          }}
          animate={{
            opacity: [0.1, 0.7, 0.1],
            scale: [1, 1.6, 1],
            y: [0, -8 - i * 2, 0],
          }}
          transition={{
            duration: 3.5 + i * 0.3,
            repeat: Infinity,
            delay: i * 0.4,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}
