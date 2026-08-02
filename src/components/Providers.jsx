"use client";

import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

const providerCategories = [
  {
    title: "Cloud Providers",
    desc: "Scale instantly with premium cloud inference architectures",
    items: [
      { name: "OpenRouter", specs: "Unified key · 150+ models · Auto-routing", type: "Cloud" },
      { name: "OpenAI", specs: "GPT-4o · GPT-4o-mini · o1 · o3-mini", type: "Cloud" },
      { name: "Anthropic", specs: "Claude 3.5 Sonnet · Claude 3.7 · 200k Context", type: "Cloud" },
      { name: "Google Gemini", specs: "Native OpenAI gateway · 2M Context · Multimodal", type: "Cloud" },
      { name: "Groq", specs: "LPU inference speed · Llama 3.3 · Mixtral", type: "Cloud" },
      { name: "DeepSeek", specs: "V3 Chat · R1 Reasoning · Low Cost", type: "Cloud" },
      { name: "Together AI", specs: "Fast open source API · Llama · Qwen", type: "Cloud" },
      { name: "Mistral AI", specs: "Mistral Large · Codestral · Embeddings", type: "Cloud" },
      { name: "Cohere", specs: "Command R+ · Multilingual · Embed v3", type: "Cloud" },
      { name: "Fireworks AI", specs: "Ultra-low latency inference · Custom models", type: "Cloud" },
      { name: "SambaNova", specs: "Fast Llama 405B execution · High context", type: "Cloud" },
      { name: "Cerebras", specs: "CS-3 execution · WSE performance", type: "Cloud" },
      { name: "xAI (Grok)", specs: "Grok 2 · Grok 2 Vision · Live search integration", type: "Cloud" }
    ]
  },
  {
    title: "Enterprise Providers",
    desc: "Secure, compliant private network integration",
    items: [
      { name: "Azure OpenAI", specs: "HIPAA/SOCI compliant private deployments", type: "Enterprise" },
      { name: "Google Vertex AI", specs: "Enterprise-grade Gemini · Vertex Embeddings", type: "Enterprise" },
      { name: "AWS Bedrock", specs: "Private AWS VPC routing · Claude · Titan", type: "Enterprise" },
      { name: "Cloudflare Workers AI", specs: "Edge execution · Low latency global routing", type: "Enterprise" }
    ]
  },
  {
    title: "Local Models",
    desc: "Run completely offline with 100% privacy and zero monthly fees",
    items: [
      { name: "Ollama", specs: "Llama 3 · Mistral · Phi 3 · Local embeddings", type: "Local" },
      { name: "LM Studio", specs: "Local server dashboard · HuggingFace loading", type: "Local" },
      { name: "vLLM", specs: "Production-grade local throughput", type: "Local" },
      { name: "LocalAI", specs: "Local companion API gateway", type: "Local" },
      { name: "llama.cpp", specs: "Ultra-lightweight native local runner", type: "Local" }
    ]
  }
];

export default function Providers() {
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
            Supported AI Ecosystem
          </motion.p>
          <h2 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
            Bring Your Own AI.
          </h2>
          <p className="mt-4 text-muted">
            NovaFlow is 100% Free and open architecture. No monthly subscription, no middleman markups. Connect any local or cloud LLM directly.
          </p>
        </motion.div>

        <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col items-center justify-center rounded-2xl border border-black/[0.05] bg-white/50 p-6 text-center shadow-sm">
            <span className="text-3xl font-serif text-neutral-800">100%</span>
            <h3 className="mt-2 text-sm font-semibold">Free Forever</h3>
            <p className="mt-1 text-xs text-muted">No subscriptions, no usage tiers, no payment gateways.</p>
          </div>
          <div className="flex flex-col items-center justify-center rounded-2xl border border-black/[0.05] bg-white/50 p-6 text-center shadow-sm">
            <span className="text-3xl font-serif text-neutral-800">BYOK</span>
            <h3 className="mt-2 text-sm font-semibold">Bring Your Own Key</h3>
            <p className="mt-1 text-xs text-muted">You own your API keys and model relationships.</p>
          </div>
          <div className="flex flex-col items-center justify-center rounded-2xl border border-black/[0.05] bg-white/50 p-6 text-center shadow-sm">
            <span className="text-3xl font-serif text-neutral-800">Offline</span>
            <h3 className="mt-2 text-sm font-semibold">Self-Hosted / Local</h3>
            <p className="mt-1 text-xs text-muted">Run Ollama or LM Studio natively with zero latency.</p>
          </div>
          <div className="flex flex-col items-center justify-center rounded-2xl border border-black/[0.05] bg-white/50 p-6 text-center shadow-sm">
            <span className="text-3xl font-serif text-neutral-800">100+</span>
            <h3 className="mt-2 text-sm font-semibold">Supported Models</h3>
            <p className="mt-1 text-xs text-muted">Fully compatible with standard chat and embedding specs.</p>
          </div>
        </div>

        <div className="mt-20 space-y-16">
          {providerCategories.map((category, idx) => (
            <motion.div
              key={category.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1, duration: 0.7, ease }}
              className="space-y-6"
            >
              <div>
                <h3 className="text-xl font-semibold text-neutral-800">{category.title}</h3>
                <p className="text-sm text-neutral-500">{category.desc}</p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {category.items.map((item) => (
                  <div
                    key={item.name}
                    className="flex flex-col justify-between rounded-xl border border-black/[0.04] bg-white/60 p-5 shadow-sm transition-all hover:bg-white hover:shadow-md"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-neutral-900">{item.name}</span>
                        <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-500 uppercase">
                          {item.type}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-muted leading-relaxed">{item.specs}</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
