import Link from "next/link";
import Navbar from "@/components/Navbar";

const features = [
  {
    title: "Unified workspace",
    description:
      "One app for chat, knowledge bases, and AI apps — no switching between tools.",
  },
  {
    title: "Knowledge & RAG",
    description:
      "Upload documents, index automatically, and ground answers in your data.",
  },
  {
    title: "Simple setup",
    description:
      "Guided onboarding, lite deploy mode, and clear health checks for local dev.",
  },
  {
    title: "Enterprise ready",
    description:
      "Roles, audit trails, and scalable backend — built for teams, not just demos.",
  },
];

const roadmap = [
  { phase: "v0.1", label: "Auth + dashboard shell", status: "in-progress" },
  { phase: "v0.2", label: "Chat & streaming", status: "planned" },
  { phase: "v0.3", label: "Knowledge upload", status: "planned" },
  { phase: "v0.4", label: "Setup wizard & templates", status: "planned" },
  { phase: "v1.0", label: "Production deploy", status: "planned" },
];

export default function HomePage() {
  return (
    <div className="flex min-h-full flex-col">
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden px-4 py-20 sm:px-6 sm:py-28">
          <div className="pointer-events-none absolute inset-0 -z-10">
            <div className="absolute left-1/2 top-0 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-indigo-500/10 blur-3xl" />
            <div className="absolute right-0 top-1/3 h-[300px] w-[400px] rounded-full bg-cyan-500/10 blur-3xl" />
          </div>
          <div className="mx-auto max-w-3xl text-center">
            <p className="mb-4 inline-flex rounded-full border border-nova-border bg-nova-surface px-4 py-1.5 text-sm text-nova-muted">
              v0.1 — Initial release in development
            </p>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
              Your AI workspace,{" "}
              <span className="nova-gradient-text">simplified</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-nova-muted">
              NovaFlow AI helps teams build chat apps, manage knowledge bases,
              and run AI workflows — with a modern interface and faster setup
              than legacy platforms.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                href="/login"
                className="nova-gradient w-full rounded-xl px-8 py-3.5 text-center text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 sm:w-auto"
              >
                Open workspace
              </Link>
              <Link
                href="/dashboard"
                className="w-full rounded-xl border border-nova-border bg-nova-surface px-8 py-3.5 text-center text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-900 sm:w-auto"
              >
                View dashboard
              </Link>
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="border-t border-nova-border bg-nova-surface px-4 py-20 sm:px-6">
          <div className="mx-auto max-w-6xl">
            <h2 className="text-center text-3xl font-bold tracking-tight">
              Built for real teams
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-center text-nova-muted">
              We focused on what matters: clarity, speed, and a single place to
              work with AI.
            </p>
            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {features.map((f) => (
                <article
                  key={f.title}
                  className="rounded-2xl border border-nova-border bg-background p-6"
                >
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-nova-muted">
                    {f.description}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Roadmap */}
        <section id="roadmap" className="px-4 py-20 sm:px-6">
          <div className="mx-auto max-w-2xl">
            <h2 className="text-center text-3xl font-bold tracking-tight">
              Roadmap
            </h2>
            <ul className="mt-10 space-y-4">
              {roadmap.map((item) => (
                <li
                  key={item.phase}
                  className="flex items-center justify-between rounded-xl border border-nova-border bg-nova-surface px-5 py-4"
                >
                  <div>
                    <span className="text-xs font-mono text-nova-muted">
                      {item.phase}
                    </span>
                    <p className="font-medium">{item.label}</p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      item.status === "in-progress"
                        ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                    }`}
                  >
                    {item.status === "in-progress" ? "In progress" : "Planned"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>

      <footer className="border-t border-nova-border py-8 text-center text-sm text-nova-muted">
        © {new Date().getFullYear()} NovaFlow AI. All rights reserved.
      </footer>
    </div>
  );
}
