"use client";

import { useEffect, useState } from "react";
import { motion, useScroll, useSpring } from "framer-motion";
import { subscribeScroll } from "@/lib/runtime/scrollBus";

export default function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 28, restDelta: 0.001 });

  return (
    <div className="pointer-events-none fixed top-0 left-0 right-0 z-[100] h-[3px] overflow-hidden">
      <motion.div
        className="absolute inset-0 origin-left bg-gradient-to-r from-neutral-400 via-black to-neutral-600"
        style={{ scaleX }}
      />
      <motion.div
        className="absolute inset-0 origin-left bg-gradient-to-r from-transparent via-white/50 to-transparent opacity-70"
        style={{ scaleX }}
      />
    </div>
  );
}

export function useNavbarScroll() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => subscribeScroll((y) => setScrolled(y > 20)), []);

  return scrolled;
}
