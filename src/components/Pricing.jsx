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
    <section id="pricing" className="px-4 py-28 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease }}
          className="mx-auto max-w-2xl text-center"
        >
          <p className="text-xs font-semibold tracking-[0.2em] text-muted uppercase">
            Pricing
          </p>
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
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.6, ease }}
              className={`relative flex flex-col rounded-[1.5rem] p-8 ${
                plan.featured
                  ? "bg-black text-white shadow-[0_32px_80px_rgba(0,0,0,0.2)]"
                  : "card"
              }`}
            >
              {plan.featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-white px-4 py-1 text-[10px] font-bold tracking-widest text-black uppercase">
                  Most popular
                </span>
              )}
              <p className={`text-sm font-medium ${plan.featured ? "text-neutral-400" : "text-muted"}`}>
                {plan.name}
              </p>
              <p className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-semibold tracking-tight">{plan.price}</span>
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
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-3 text-sm">
                    <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                      plan.featured ? "bg-white/10" : "bg-surface"
                    }`}>
                      ✓
                    </span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href={plan.href}
                className={`mt-8 inline-flex items-center justify-center rounded-full py-3 text-sm font-semibold transition-all hover:scale-[1.02] ${
                  plan.featured
                    ? "bg-white text-black hover:shadow-xl"
                    : "btn-primary w-full"
                }`}
              >
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
