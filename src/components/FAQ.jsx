"use client";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

const faqs = [
  {
    q: "What is NovaFlow AI?",
    a: "NovaFlow is a unified AI workspace that brings chat, knowledge bases, and workflow automation into one beautifully designed platform — powered by enterprise-grade infrastructure.",
  },
  {
    q: "How does it connect to my data?",
    a: "Upload documents to knowledge bases, connect APIs, or link existing data sources. NovaFlow uses RAG to ground every AI response in your actual content.",
  },
  {
    q: "Is it suitable for teams?",
    a: "Yes. Role-based access, audit logs, and team workspaces are built in from day one. Scale from a solo builder to an entire organization.",
  },
  {
    q: "Can I use my own AI models?",
    a: "Absolutely. Connect OpenAI, Anthropic, local models via Ollama, or any OpenAI-compatible endpoint. Switch models per assistant.",
  },
  {
    q: "How do I get started?",
    a: "Create a free account, connect your backend, and launch your first assistant in minutes. No credit card required during beta.",
  },
];

const container = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.15 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease } },
};

export default function FAQ() {
  const [open, setOpen] = useState(0);

  return (
    <section id="faq" className="border-t border-border bg-surface px-4 py-28 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease }}
          className="text-center"
        >
          <p className="text-xs font-semibold tracking-[0.2em] text-muted uppercase">FAQ</p>
          <h2 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
            Questions, answered.
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-40px" }}
          className="mt-14 space-y-3"
        >
          {faqs.map((faqItem, i) => (
            <motion.div key={faqItem.q} variants={item}>
              <FAQItem
                item={faqItem}
                isOpen={open === i}
                onToggle={() => setOpen(open === i ? -1 : i)}
              />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function FAQItem({ item, isOpen, onToggle }) {
  const ref = useRef(null);

  return (
    <motion.div
      layout
      whileHover={{ borderColor: "rgba(0,0,0,0.15)" }}
      className={`overflow-hidden rounded-2xl border bg-white transition-colors ${
        isOpen ? "border-neutral-300 shadow-sm" : "border-border"
      }`}
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
      >
        <motion.span
          animate={{ color: isOpen ? "#0a0a0a" : "#525252" }}
          className="font-medium"
        >
          {item.q}
        </motion.span>
        <motion.span
          animate={{ rotate: isOpen ? 45 : 0, backgroundColor: isOpen ? "rgba(0,0,0,0.06)" : "transparent" }}
          transition={{ duration: 0.3, ease }}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border text-sm"
        >
          +
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            ref={ref}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease }}
          >
            <motion.p
              initial={{ y: -8 }}
              animate={{ y: 0 }}
              exit={{ y: -4 }}
              transition={{ duration: 0.3, ease }}
              className="border-t border-border px-6 pb-5 pt-3 text-sm leading-relaxed text-muted"
            >
              {item.a}
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
