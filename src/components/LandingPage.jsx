"use client";

import Link from "next/link";
import { useEffect } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { subscribePointer } from "@/lib/runtime/pointerBus";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ScrollProgress from "@/components/ScrollProgress";
import HeroMockup from "@/components/HeroMockup";
import AnimatedCounter from "@/components/AnimatedCounter";
import LiveBackground from "@/components/LiveBackground";
import LiveAIActivity, { LiveAIGlobe } from "@/components/LiveAIActivity";
import LiveMetric from "@/components/LiveMetric";
import PageLoader from "@/components/PageLoader";
import BackToTop from "@/components/BackToTop";
import CursorGlow from "@/components/CursorGlow";
import Magnetic from "@/components/Magnetic";
import FAQ from "@/components/FAQ";
import Pricing from "@/components/Pricing";
import CodeShowcase from "@/components/CodeShowcase";
import PlatformSection from "@/components/PlatformSection";
import WorkflowShowcase from "@/components/landing/WorkflowShowcase";
import { StaggerText } from "@/components/Reveal";

const ease = [0.16, 1, 0.3, 1];

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.8, delay: i * 0.12, ease },
  }),
};

const stats = [
  { value: "10", suffix: "x", label: "Faster deployment" },
  { value: "99", suffix: "%", label: "Uptime SLA" },
  { value: "50", suffix: "+", label: "Enterprise features" },
  { value: "24", suffix: "/7", label: "Always available" },
];

const testimonials = [
  {
    quote: "NovaFlow replaced three tools for us. The interface is impossibly clean.",
    author: "Sarah Chen",
    role: "Head of Product, North Labs",
    avatar: "SC",
  },
  {
    quote: "We went from prototype to production in a week. The setup wizard is brilliant.",
    author: "Marcus Webb",
    role: "CTO, ScaleFlow",
    avatar: "MW",
  },
  {
    quote: "Finally an AI platform that feels designed, not assembled.",
    author: "Elena Rodriguez",
    role: "VP Engineering, DataPrime",
    avatar: "ER",
  },
];

const logos = [
  "North Labs", "Vertex AI", "ScaleFlow", "DataPrime", "Acme Corp",
  "CloudNine", "Synapse", "Orbital",
];

export default function LandingPage() {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 50, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 50, damping: 20 });
  const heroX = useTransform(springX, [-1, 1], [-16, 16]);
  const heroY = useTransform(springY, [-1, 1], [-10, 10]);
  const mockX = useTransform(springX, [-1, 1], [14, -14]);
  const mockY = useTransform(springY, [-1, 1], [10, -10]);

  useEffect(() => {
    const w = () => window.innerWidth;
    const h = () => window.innerHeight;
    return subscribePointer((clientX, clientY, active) => {
      if (!active) return;
      mouseX.set((clientX / w()) * 2 - 1);
      mouseY.set((clientY / h()) * 2 - 1);
    });
  }, [mouseX, mouseY]);

  return (
    <div className="relative min-h-screen text-foreground">
      {/* Full-page live background + AI data streams */}
      <div className="fixed inset-0 z-0">
        <LiveBackground variant="light" showNetwork mouseTracking />
        <LiveAIGlobe />
      </div>

      <div className="relative z-10 min-h-screen noise">
      <PageLoader />
      <ScrollProgress />
      <Navbar />
      <BackToTop />
      <CursorGlow />

      {/* Hero */}
      <section className="relative overflow-hidden pt-32 pb-24 sm:pt-40 sm:pb-32">
        <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
          <motion.div style={{ x: heroX, y: heroY }} className="mx-auto max-w-4xl text-center">
            <motion.div
              initial="hidden"
              animate="visible"
              variants={fadeUp}
              custom={0}
              whileHover={{ scale: 1.03 }}
              className="mb-8 inline-flex items-center gap-2.5 rounded-full border border-border bg-white/90 px-5 py-2 text-xs font-medium tracking-[0.2em] uppercase shadow-sm backdrop-blur-xl"
            >
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-40" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
              <span className="text-green-700">AI Live</span>
              <span className="text-muted">· Public beta</span>
            </motion.div>

            <motion.h1
              initial="hidden"
              animate="visible"
              variants={fadeUp}
              custom={1}
              className="font-serif text-[2.75rem] leading-[1.08] tracking-tight sm:text-6xl lg:text-[5.25rem]"
            >
              <StaggerText text="AI infrastructure" />
              <br />
              <motion.span
                initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.7, delay: 0.7, ease }}
                className="text-gradient italic"
              >
                for serious teams.
              </motion.span>
            </motion.h1>

            <motion.p
              initial="hidden"
              animate="visible"
              variants={fadeUp}
              custom={2}
              className="mx-auto mt-7 max-w-2xl text-lg leading-relaxed text-muted sm:text-xl"
            >
              NovaFlow AI unifies chat, knowledge, and workflows in one
              meticulously crafted workspace — built for speed, clarity, and
              scale.
            </motion.p>

            <motion.div
              initial="hidden"
              animate="visible"
              variants={fadeUp}
              custom={3}
              className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
            >
              <Magnetic strength={0.35}>
                <Link href="/login?mode=register" className="group btn-primary w-full sm:w-auto">
                  Start building free
                  <span aria-hidden className="transition-transform group-hover:translate-x-1">→</span>
                </Link>
              </Magnetic>
              <Magnetic strength={0.25}>
                <Link href="#bento" className="btn-secondary w-full sm:w-auto">
                  See the platform
                </Link>
              </Magnetic>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2, duration: 0.8 }}
              className="mt-12 flex items-center justify-center gap-6 text-xs text-muted"
            >
              <span className="flex items-center gap-2">
                <span className="text-green-500">●</span> No credit card
              </span>
              <span className="flex items-center gap-2">
                <span className="text-green-500">●</span> Free during beta
              </span>
              <span className="hidden items-center gap-2 sm:flex">
                <span className="text-green-500">●</span> Setup in 2 min
              </span>
            </motion.div>

            <LiveAIActivity />
          </motion.div>

          <motion.div
            style={{ x: mockX, y: mockY }}
            initial={{ opacity: 0, y: 48, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 1, delay: 0.5, ease }}
            className="relative mx-auto mt-20 max-w-4xl"
          >
            <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-b from-white/80 via-neutral-100/40 to-transparent blur-2xl" />
            <HeroMockup />
            <div className="absolute -left-6 top-1/4 hidden lg:block">
              <LiveMetric label="Latency" value={42} suffix="ms" />
            </div>
            <div className="absolute -right-6 bottom-1/4 hidden lg:block">
              <LiveMetric label="Accuracy" value={99} suffix="%" dark />
            </div>
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 2 }}
              className="absolute -right-2 -top-4 hidden rounded-xl border border-border bg-white/90 px-3 py-2 shadow-lg backdrop-blur-sm lg:block"
            >
              <div className="flex items-center gap-2">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-50" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-green-500" />
                </span>
                <p className="text-[10px] font-medium text-green-700">AI processing</p>
              </div>
              <p className="mt-1 text-lg font-semibold tabular-nums">2,400+ users</p>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border/80 bg-white/75 backdrop-blur-lg">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-border md:grid-cols-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08, duration: 0.6, ease }}
              className="group px-6 py-10 text-center transition-colors hover:bg-white/80 sm:px-8"
            >
              <p className="text-3xl font-semibold tracking-tight sm:text-4xl">
                <AnimatedCounter value={stat.value} suffix={stat.suffix} />
              </p>
              <p className="mt-2 text-sm text-muted">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Marquee */}
      <section className="overflow-hidden py-8 marquee-fade">
        <div className="flex whitespace-nowrap animate-marquee">
          {[...logos, ...logos].map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="mx-10 text-sm font-medium tracking-[0.25em] text-muted/60 uppercase transition-colors hover:text-muted"
            >
              {name}
            </span>
          ))}
        </div>
      </section>

      <PlatformSection />

      <CodeShowcase />

      <WorkflowShowcase />

      <Pricing />

      {/* Testimonials */}
      <section id="testimonials" className="px-4 py-28 sm:px-6">
        <div className="mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease }}
            className="text-center"
          >
            <p className="text-xs font-semibold tracking-[0.2em] text-muted uppercase">Stories</p>
            <h2 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
              Trusted by forward-thinking teams
            </h2>
          </motion.div>
          <div className="mt-16 grid gap-6 md:grid-cols-3">
            {testimonials.map((t, i) => (
              <motion.blockquote
                key={t.author}
                initial={{ opacity: 0, y: 36, rotateX: 8 }}
                whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ delay: i * 0.12, duration: 0.65, ease }}
                whileHover={{
                  y: -6,
                  boxShadow: "0 24px 60px rgba(0,0,0,0.08)",
                  transition: { duration: 0.25 },
                }}
                className="card card-hover flex flex-col justify-between p-8 transition-shadow"
              >
                <div className="mb-6 flex gap-1">
                  {[...Array(5)].map((_, j) => (
                    <motion.span
                      key={j}
                      initial={{ opacity: 0, scale: 0 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.3 + i * 0.1 + j * 0.05, type: "spring", stiffness: 400 }}
                      className="text-amber-400"
                    >
                      ★
                    </motion.span>
                  ))}
                </div>
                <motion.p
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.35 + i * 0.1, duration: 0.5 }}
                  className="text-base leading-relaxed text-foreground"
                >
                  &ldquo;{t.quote}&rdquo;
                </motion.p>
                <footer className="mt-8 flex items-center gap-4 border-t border-border pt-6">
                  <motion.span
                    whileHover={{ scale: 1.08, rotate: 3 }}
                    className="flex h-10 w-10 items-center justify-center rounded-full bg-black text-xs font-bold text-white"
                  >
                    {t.avatar}
                  </motion.span>
                  <div>
                    <p className="font-semibold">{t.author}</p>
                    <p className="text-sm text-muted">{t.role}</p>
                  </div>
                </footer>
              </motion.blockquote>
            ))}
          </div>
        </div>
      </section>

      <FAQ />

      {/* CTA */}
      <section className="px-4 pb-28 sm:px-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 32 }}
          whileInView={{ opacity: 1, scale: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.85, ease }}
          className="relative mx-auto max-w-4xl overflow-hidden rounded-[2rem] bg-black px-8 py-20 text-center text-white sm:px-16"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.08),transparent_50%)]" />
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
            className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full border border-white/5"
          />
          <motion.div
            animate={{ rotate: -360 }}
            transition={{ duration: 80, repeat: Infinity, ease: "linear" }}
            className="pointer-events-none absolute -bottom-32 -left-32 h-96 w-96 rounded-full border border-white/5"
          />
          {[...Array(6)].map((_, i) => (
            <motion.span
              key={i}
              className="pointer-events-none absolute h-1 w-1 rounded-full bg-white/30"
              style={{
                left: `${15 + i * 14}%`,
                top: `${20 + (i % 3) * 25}%`,
              }}
              animate={{
                opacity: [0.2, 0.8, 0.2],
                scale: [1, 1.8, 1],
                y: [0, -12, 0],
              }}
              transition={{
                duration: 3 + i * 0.4,
                repeat: Infinity,
                delay: i * 0.5,
                ease: "easeInOut",
              }}
            />
          ))}
          <div className="relative">
            <motion.h2
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.15, duration: 0.6, ease }}
              className="font-serif text-4xl tracking-tight sm:text-5xl"
            >
              Start building today.
            </motion.h2>
            <motion.p
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="mx-auto mt-4 max-w-md text-neutral-400"
            >
              Join teams using NovaFlow to ship AI products with confidence.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.45, duration: 0.5, ease }}
              className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
            >
              <Magnetic strength={0.3}>
                <Link
                  href="/login?mode=register"
                  className="inline-flex items-center justify-center rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-black transition-all hover:scale-105 hover:shadow-2xl"
                >
                  Create free account
                </Link>
              </Magnetic>
              <Link
                href="/login"
                className="inline-flex items-center justify-center rounded-full border border-white/20 px-8 py-3.5 text-sm font-semibold text-white transition-all hover:border-white/40 hover:bg-white/10"
              >
                Sign in
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </section>

      <Footer />
      </div>
    </div>
  );
}
