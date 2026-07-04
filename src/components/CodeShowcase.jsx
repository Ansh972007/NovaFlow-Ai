"use client";

import { motion } from "framer-motion";

const ease = [0.16, 1, 0.3, 1];

const code = `// Connect your assistant in seconds
const assistant = await novaflow.create({
  name: "Support Bot",
  model: "gpt-4o",
  knowledge: ["docs", "policies"],
  tools: ["search", "email"],
});

await assistant.deploy({ team: "support" });`;

export default function CodeShowcase() {
  return (
    <section className="overflow-hidden px-4 py-28 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-20">
          <motion.div
            initial={{ opacity: 0, x: -32 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease }}
          >
            <p className="text-xs font-semibold tracking-[0.2em] text-muted uppercase">
              Developer-first
            </p>
            <h2 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
              Ship faster with
              <span className="italic text-muted"> clean APIs.</span>
            </h2>
            <p className="mt-5 max-w-md text-muted leading-relaxed">
              Every feature is accessible programmatically. Build custom
              integrations, automate deployments, and embed AI anywhere.
            </p>
            <ul className="mt-8 space-y-4">
              {["REST & WebSocket APIs", "Streaming responses", "Webhook events"].map(
                (item, i) => (
                  <motion.li
                    key={item}
                    initial={{ opacity: 0, x: -16 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.2 + i * 0.1, duration: 0.5, ease }}
                    className="flex items-center gap-3 text-sm"
                  >
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-black text-[10px] text-white">
                      →
                    </span>
                    {item}
                  </motion.li>
                )
              )}
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 32 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease }}
            className="gradient-border shadow-[0_32px_80px_rgba(0,0,0,0.1)]"
          >
            <div className="overflow-hidden rounded-[1.2rem] bg-[#0a0a0a]">
              <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
                <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
                <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
                <span className="h-3 w-3 rounded-full bg-[#28c840]" />
                <span className="ml-3 text-[11px] text-neutral-500">deploy.ts</span>
              </div>
              <pre className="overflow-x-auto p-6 text-[13px] leading-relaxed">
                <code>
                  {code.split("\n").map((line, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -8 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.3 + i * 0.06, duration: 0.4, ease }}
                    >
                      <span className="mr-4 inline-block w-6 select-none text-right text-neutral-600">
                        {i + 1}
                      </span>
                      <span className="text-neutral-300">{highlightLine(line)}</span>
                    </motion.div>
                  ))}
                </code>
              </pre>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function highlightLine(line) {
  if (line.startsWith("//")) {
    return <span className="text-neutral-500">{line}</span>;
  }
  return line.split(/(".*?"|'.*?'|`.*?`)/g).map((part, i) => {
    if (part.startsWith('"') || part.startsWith("'")) {
      return (
        <span key={i} className="text-emerald-400">
          {part}
        </span>
      );
    }
    if (part.includes("await") || part.includes("const")) {
      return (
        <span key={i}>
          {part.split(/\b(await|const)\b/).map((p, j) =>
            p === "await" || p === "const" ? (
              <span key={j} className="text-purple-400">{p}</span>
            ) : (
              p
            )
          )}
        </span>
      );
    }
    return part;
  });
}
