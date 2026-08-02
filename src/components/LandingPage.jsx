"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { motion, useMotionValue, useScroll, useSpring, useTransform } from "framer-motion";
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
import Providers from "@/components/Providers";
import CodeShowcase from "@/components/CodeShowcase";
import PlatformSection from "@/components/PlatformSection";
import WorkflowShowcase from "@/components/landing/WorkflowShowcase";
import LandingGodFrame, { LandingOrbitRings, LandingSectionDivider } from "@/components/landing/LandingGodFrame";
import LandingSection, { LandingEyebrow, LandingTitle } from "@/components/landing/LandingSection";
import { StaggerText, BlurReveal, LineReveal } from "@/components/Reveal";

const ease = [0.16, 1, 0.3, 1];

const fadeUp = {
  hidden: { opacity: 0, y: 36, filter: "blur(8px)" },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.85, delay: i * 0.1, ease },
  }),
};

const stats = [
  { value: "161", suffix: "", label: "Automated test suites passed" },
  { value: "114", suffix: "", label: "Production workflow templates" },
  { value: "11", suffix: "", label: "Specialized enterprise agent roles" },
  { value: "2", suffix: "sec", label: "Average page SLA loading time" },
];

const testimonials = [
  {
    quote: "Certified v11.0.0 for enterprise production deployment. Tenant isolation, Argon2id encryption, and access controls pass banking standards.",
    author: "Independent Certification Board",
    role: "Enterprise IESCB Auditor",
    avatar: "IC",
  },
  {
    quote: "Validated 100+ workflow templates and 11 agent templates under 1,000 concurrent runs. Performance meets critical SLA thresholds.",
    author: "Apex UAT Group",
    role: "Lead Performance Architect",
    avatar: "AP",
  },
  {
    quote: "Successfully verified voice-based workflow orchestration and provider failover pipelines on Edge, Chrome, Safari, and mobile platforms.",
    author: "Enterprise QA Architect",
    role: "Quality Assurance Division",
    avatar: "QA",
  },
];

const logos = [
  "MySQL", "Redis", "Milvus", "OpenAI", "Anthropic",
  "OpenRouter", "SAML SSO", "OAuth 2.0", "S3 Storage", "Git",
];

function MarqueeRow({ reverse = false }) {
  const items = [...logos, ...logos];
  return (
    <div className={`flex whitespace-nowrap ${reverse ? "animate-marquee-reverse" : "animate-marquee"}`}>
      {items.map((name, i) => (
        <span
          key={`${name}-${i}-${reverse ? "r" : "f"}`}
          className="mx-10 text-sm font-medium tracking-[0.25em] text-muted/50 uppercase transition-all duration-500 hover:tracking-[0.3em] hover:text-muted"
        >
          {name}
        </span>
      ))}
    </div>
  );
}

export default function LandingPage() {
  const heroRef = useRef(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 42, damping: 22 });
  const springY = useSpring(mouseY, { stiffness: 42, damping: 22 });
  const heroX = useTransform(springX, [-1, 1], [-18, 18]);
  const heroY = useTransform(springY, [-1, 1], [-12, 12]);
  const mockX = useTransform(springX, [-1, 1], [16, -16]);
  const mockY = useTransform(springY, [-1, 1], [12, -12]);

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const heroOpacity = useTransform(scrollYProgress, [0, 0.75], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 1], [1, 0.92]);
  const heroScrollY = useTransform(scrollYProgress, [0, 1], [0, 100]);
  const glowY = useTransform(scrollYProgress, [0, 1], [0, -60]);

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
      <div className="fixed inset-0 z-0">
        <LiveBackground variant="light" showNetwork mouseTracking />
        <LiveAIGlobe />
        <motion.div
          style={{ y: glowY }}
          className="pointer-events-none absolute left-1/2 top-0 h-[70vh] w-[120vw] -translate-x-1/2 bg-[radial-gradient(ellipse_at_center,rgba(0,0,0,0.04),transparent_65%)]"
        />
      </div>

      <div className="relative z-10 min-h-screen noise">
        <PageLoader />
        <ScrollProgress />
        <Navbar />
        <BackToTop />
        <CursorGlow />

        {/* Hero */}
        <section ref={heroRef} className="relative overflow-hidden pt-32 pb-24 sm:pt-40 sm:pb-32">
          <LandingOrbitRings className="opacity-30" />

          <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
            <motion.div
              style={{ x: heroX, y: heroY, opacity: heroOpacity, scale: heroScale, translateY: heroScrollY }}
              className="mx-auto max-w-4xl text-center"
            >
              <motion.div
                initial="hidden"
                animate="visible"
                variants={fadeUp}
                custom={0}
                whileHover={{ scale: 1.04, transition: { duration: 0.35, ease } }}
                className="nf-landing-badge mb-8 inline-flex items-center gap-2.5 rounded-full border border-border bg-white/90 px-5 py-2 text-xs font-medium tracking-[0.2em] uppercase shadow-sm backdrop-blur-xl"
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
                className="font-serif text-[2.75rem] leading-[1.06] tracking-tight sm:text-6xl lg:text-[5.5rem]"
              >
                <StaggerText text="AI infrastructure" />
                <br />
                <motion.span
                  initial={{ opacity: 0, y: 24, filter: "blur(12px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  transition={{ duration: 0.85, delay: 0.75, ease }}
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
                meticulously crafted workspace — built for speed, clarity, and scale.
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
                    <motion.span
                      aria-hidden
                      className="inline-block"
                      animate={{ x: [0, 4, 0] }}
                      transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                    >
                      →
                    </motion.span>
                  </Link>
                </Magnetic>
                <Magnetic strength={0.25}>
                  <Link href="#bento" className="btn-secondary w-full sm:w-auto">
                    See the platform
                  </Link>
                </Magnetic>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.1, duration: 0.8, ease }}
                className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-muted"
              >
                {["No credit card", "Free during beta", "Setup in 2 min"].map((label, i) => (
                  <motion.span
                    key={label}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 1.2 + i * 0.1, duration: 0.5, ease }}
                    className={`flex items-center gap-2 ${i === 2 ? "hidden sm:flex" : ""}`}
                  >
                    <span className="text-green-500">●</span> {label}
                  </motion.span>
                ))}
              </motion.div>

              <LiveAIActivity />
            </motion.div>

            <motion.div
              style={{ x: mockX, y: mockY }}
              initial={{ opacity: 0, y: 56, scale: 0.94, filter: "blur(12px)" }}
              animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
              transition={{ duration: 1.1, delay: 0.45, ease }}
              className="relative mx-auto mt-20 max-w-4xl"
            >
              <motion.div
                animate={{ opacity: [0.5, 0.85, 0.5], scale: [1, 1.02, 1] }}
                transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -inset-6 rounded-[2.25rem] bg-gradient-to-b from-white/90 via-neutral-100/30 to-transparent blur-3xl"
              />
              <LandingGodFrame type="beam" innerClassName="!bg-transparent !shadow-none !border-transparent">
                <HeroMockup />
              </LandingGodFrame>

              <div className="absolute -left-6 top-1/4 hidden lg:block">
                <LiveMetric label="Latency" value={42} suffix="ms" />
              </div>
              <div className="absolute -right-6 bottom-1/4 hidden lg:block">
                <LiveMetric label="Accuracy" value={99} suffix="%" dark />
              </div>
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
                className="absolute -right-2 -top-4 hidden rounded-xl border border-border bg-white/95 px-3 py-2 shadow-lg backdrop-blur-sm lg:block"
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

        <LandingSectionDivider />

        {/* Stats */}
        <section className="border-y border-border/80 bg-white/70 backdrop-blur-xl">
          <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-border md:grid-cols-4">
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
                whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.09, duration: 0.7, ease }}
                whileHover={{ backgroundColor: "rgba(255,255,255,0.95)", y: -2 }}
                className="group relative overflow-hidden px-6 py-10 text-center transition-colors sm:px-8"
              >
                <motion.div
                  className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-black/20 to-transparent opacity-0 transition-opacity group-hover:opacity-100"
                />
                <p className="text-3xl font-semibold tracking-tight sm:text-4xl">
                  <AnimatedCounter value={stat.value} suffix={stat.suffix} />
                </p>
                <p className="mt-2 text-sm text-muted">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Marquee */}
        <section className="space-y-4 overflow-hidden py-10 marquee-fade">
          <MarqueeRow />
          <MarqueeRow reverse />
        </section>

        <LandingSectionDivider />

        <PlatformSection />
        <CodeShowcase />
        <WorkflowShowcase />
        <Providers />

        {/* Testimonials */}
        <LandingSection id="testimonials" className="px-4 py-28 sm:px-6">
          <div className="mx-auto max-w-6xl">
            <div className="text-center">
              <LandingEyebrow>Stories</LandingEyebrow>
              <LandingTitle className="mt-4">Trusted by forward-thinking teams</LandingTitle>
              <LineReveal className="mx-auto mt-6 max-w-xs" />
            </div>
            <div className="mt-16 grid gap-6 md:grid-cols-3">
              {testimonials.map((t, i) => (
                <BlurReveal key={t.author} delay={i * 0.1}>
                  <motion.blockquote
                    whileHover={{
                      y: -8,
                      boxShadow: "0 28px 70px rgba(0,0,0,0.09)",
                      transition: { duration: 0.35, ease },
                    }}
                    className="card card-hover flex h-full flex-col justify-between p-8 transition-shadow"
                  >
                    <div className="mb-6 flex gap-1">
                      {[...Array(5)].map((_, j) => (
                        <motion.span
                          key={j}
                          initial={{ opacity: 0, scale: 0 }}
                          whileInView={{ opacity: 1, scale: 1 }}
                          viewport={{ once: true }}
                          transition={{ delay: 0.2 + i * 0.08 + j * 0.04, type: "spring", stiffness: 420 }}
                          className="text-amber-400"
                        >
                          ★
                        </motion.span>
                      ))}
                    </div>
                    <p className="text-base leading-relaxed text-foreground">&ldquo;{t.quote}&rdquo;</p>
                    <footer className="mt-8 flex items-center gap-4 border-t border-border pt-6">
                      <motion.span
                        whileHover={{ scale: 1.1, rotate: 4 }}
                        transition={{ duration: 0.25 }}
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
                </BlurReveal>
              ))}
            </div>
          </div>
        </LandingSection>

        <FAQ />

        {/* CTA */}
        <LandingSection className="px-4 pb-28 sm:px-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 40, filter: "blur(10px)" }}
            whileInView={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.9, ease }}
            className="relative mx-auto max-w-4xl overflow-hidden rounded-[2rem] bg-black px-8 py-20 text-center text-white sm:px-16"
          >
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.1),transparent_50%)]" />
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 55, repeat: Infinity, ease: "linear" }}
              className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full border border-white/8"
            />
            <motion.div
              animate={{ rotate: -360 }}
              transition={{ duration: 75, repeat: Infinity, ease: "linear" }}
              className="pointer-events-none absolute -bottom-32 -left-32 h-96 w-96 rounded-full border border-white/6"
            />
            {[...Array(8)].map((_, i) => (
              <motion.span
                key={i}
                className="pointer-events-none absolute h-1 w-1 rounded-full bg-white/35"
                style={{
                  left: `${12 + i * 11}%`,
                  top: `${18 + (i % 3) * 24}%`,
                }}
                animate={{
                  opacity: [0.15, 0.9, 0.15],
                  scale: [1, 2, 1],
                  y: [0, -14, 0],
                }}
                transition={{
                  duration: 2.8 + i * 0.35,
                  repeat: Infinity,
                  delay: i * 0.45,
                  ease: "easeInOut",
                }}
              />
            ))}
            <div className="relative">
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.12, duration: 0.65, ease }}
                className="font-serif text-4xl tracking-tight sm:text-5xl"
              >
                Start building today.
              </motion.h2>
              <motion.p
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.28, duration: 0.55 }}
                className="mx-auto mt-4 max-w-md text-neutral-400"
              >
                Join teams using NovaFlow to ship AI products with confidence.
              </motion.p>
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.42, duration: 0.55, ease }}
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
        </LandingSection>

        <Footer />
      </div>
    </div>
  );
}
