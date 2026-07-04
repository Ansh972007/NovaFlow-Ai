"use client";

import { useEffect } from "react";
import { motion, useMotionTemplate, useMotionValue, useSpring } from "framer-motion";

export default function CursorGlow() {
  const mouseX = useMotionValue(-500);
  const mouseY = useMotionValue(-500);
  const springX = useSpring(mouseX, { stiffness: 80, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 80, damping: 20 });

  const glow = useMotionTemplate`radial-gradient(520px circle at ${springX}px ${springY}px, rgba(0,0,0,0.07), transparent 65%)`;
  const ring = useMotionTemplate`radial-gradient(180px circle at ${springX}px ${springY}px, rgba(0,0,0,0.04), transparent 70%)`;

  useEffect(() => {
    const move = (e) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };
    window.addEventListener("mousemove", move, { passive: true });
    return () => window.removeEventListener("mousemove", move);
  }, [mouseX, mouseY]);

  return (
    <>
      <motion.div
        className="pointer-events-none fixed inset-0 z-[5] hidden md:block"
        style={{ background: glow }}
        aria-hidden
      />
      <motion.div
        className="pointer-events-none fixed inset-0 z-[5] hidden md:block"
        style={{ background: ring }}
        aria-hidden
      />
    </>
  );
}
