"use client";

import { useEffect, useState } from "react";
import { motion, useScroll, useSpring } from "framer-motion";
import { subscribeScroll } from "@/lib/runtime/scrollBus";

export default function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  return (
    <motion.div
      className="scroll-progress fixed top-0 left-0 right-0 z-[100] h-[2px] bg-black origin-left"
      style={{ scaleX }}
    />
  );
}

export function useNavbarScroll() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => subscribeScroll((y) => setScrolled(y > 20)), []);

  return scrolled;
}
