"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

const plans = [
  {
    name: "Starter",
    price: "Free",
    desc: "For individuals exploring AI",
    features: ["1 assistant", "Basic chat", "Community support"],
    cta: "Get started",
    href: "/login?mode=register",
    featured: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/mo",
    desc: "For growing teams",
    features: ["Unlimited assistants", "Knowledge RAG", "Priority support", "Team seats"],
    cta: "Start free trial",
    href: "/login?mode=register",
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    desc: "For organizations at scale",
    features: ["SSO & SAML", "Dedicated infra", "SLA guarantee", "Custom integrations"],
    cta: "Contact sales",
    href: "/login",
    featured: false,
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="relative overflow-hidden px-4 py-28 sm:px-6">
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -right-40 top-20 h-80 w-80 rounded-full bg-violet-100/40 blur-[100px]"
        animate={{ scale: [1, 1.15, 1], opacity: [0.4, 0.6, 0.4] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="relative mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.75, ease }}
          className="mx-auto max-w-2xl text-center"
        >
          <motion.p
            initial={{ opacity: 0, letterSpacing: "0.35em" }}
            whileInView={{ opacity: 1, letterSpacing: "0.2em" }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease }}
            className="text-xs font-semibold text-muted uppercase"
          >
            Pricing
          </motion.p>
          <h2 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
            Simple, transparent plans.
          </h2>
          <p className="mt-4 text-muted">
            Start free. Upgrade when you&apos;re ready. No hidden fees.
          </p>
        </motion.div>

        <div className="mt-16 grid gap-6 lg:grid-cols-3">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 40, scale: 0.96 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-30px" }}
              transition={{ delay: i * 0.12, duration: 0.65, ease }}
              whileHover={{
                y: plan.featured ? -10 : -6,
                transition: { duration: 0.25 },
              }}
              className={`relative flex flex-col rounded-[1.5rem] p-8 transition-shadow duration-500 ${
                plan.featured
                  ? "bg-black text-white shadow-[0_32px_80px_rgba(0,0,0,0.25)] ring-1 ring-white/10"
                  : "card hover:shadow-[0_20px_50px_rgba(0,0,0,0.06)]"
              }`}
            >
              {plan.featured && (
                <>
                  <motion.span
                    initial={{ opacity: 0, y: -8 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.3 + i * 0.1, ease }}
                    className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-white px-4 py-1 text-[10px] font-bold tracking-widest text-black uppercase"
                  >
                    Most popular
                  </motion.span>
                  <motion.div
                    className="pointer-events-none absolute inset-0 rounded-[1.5rem] opacity-30"
                    animate={{ backgroundPosition: ["0% 0%", "100% 100%"] }}
                    transition={{ duration: 6, repeat: Infinity, repeatType: "reverse" }}
                    style={{
                      background:
                        "linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 50%, rgba(255,255,255,0.05) 100%)",
                      backgroundSize: "200% 200%",
                    }}
                  />
                </>
              )}
              <p className={`text-sm font-medium ${plan.featured ? "text-neutral-400" : "text-muted"}`}>
                {plan.name}
              </p>
              <p className="mt-4 flex items-baseline gap-1">
                <motion.span
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 + i * 0.1, type: "spring", stiffness: 200 }}
                  className="text-4xl font-semibold tracking-tight"
                >
                  {plan.price}
                </motion.span>
                {plan.period && (
                  <span className={`text-sm ${plan.featured ? "text-neutral-500" : "text-muted"}`}>
                    {plan.period}
                  </span>
                )}
              </p>
              <p className={`mt-2 text-sm ${plan.featured ? "text-neutral-400" : "text-muted"}`}>
                {plan.desc}
              </p>
              <ul className="mt-8 flex-1 space-y-3">
                {plan.features.map((f, fi) => (
                  <motion.li
                    key={f}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.35 + i * 0.08 + fi * 0.06, duration: 0.4, ease }}
                    className="flex items-center gap-3 text-sm"
                  >
                    <motion.span
                      whileHover={{ scale: 1.15, rotate: 5 }}
                      className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                        plan.featured ? "bg-white/10" : "bg-surface"
                      }`}
                    >
                      ✓
                    </motion.span>
                    {f}
                  </motion.li>
                ))}
              </ul>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Link
                  href={plan.href}
                  className={`mt-8 inline-flex w-full items-center justify-center rounded-full py-3 text-sm font-semibold transition-all ${
                    plan.featured
                      ? "bg-white text-black hover:shadow-xl"
                      : "btn-primary"
                  }`}
                >
                  {plan.cta}
                </Link>
              </motion.div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
