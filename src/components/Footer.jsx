import Link from "next/link";
import Logo from "./Logo";

export default function Footer() {
  return (
    <footer className="relative border-t border-border bg-white">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-black/20 to-transparent" />
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-12 md:grid-cols-4">
          <div className="md:col-span-2">
            <Logo size="sm" />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted">
              The professional AI workspace for teams who ship fast and think
              clearly.
            </p>
            <div className="mt-6 flex gap-3">
              {["X", "GitHub", "LinkedIn"].map((s) => (
                <span
                  key={s}
                  className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full border border-border text-xs font-medium text-muted transition-all hover:border-foreground hover:text-foreground"
                >
                  {s === "X" ? "𝕏" : s === "GitHub" ? "GH" : "in"}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold tracking-widest text-muted uppercase">
              Product
            </p>
            <ul className="mt-4 space-y-3 text-sm text-muted">
              <li><Link href="#features" className="transition-colors hover:text-foreground">Features</Link></li>
              <li><Link href="#pricing" className="transition-colors hover:text-foreground">Pricing</Link></li>
              <li><Link href="/chat" className="transition-colors hover:text-foreground">Chat</Link></li>
              <li><Link href="/dashboard" className="transition-colors hover:text-foreground">Dashboard</Link></li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold tracking-widest text-muted uppercase">
              Company
            </p>
            <ul className="mt-4 space-y-3 text-sm text-muted">
              <li><Link href="#faq" className="transition-colors hover:text-foreground">FAQ</Link></li>
              <li><Link href="/docs" className="transition-colors hover:text-foreground">Docs</Link></li>
              <li><Link href="/login" className="transition-colors hover:text-foreground">Sign in</Link></li>
              <li><Link href="/login?mode=register" className="transition-colors hover:text-foreground">Register</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-border pt-8 sm:flex-row">
          <p className="text-xs text-muted">
            © {new Date().getFullYear()} NovaFlow AI. All rights reserved.
          </p>
          <div className="flex gap-6 text-xs text-muted-light">
            <span className="cursor-pointer transition-colors hover:text-foreground">Privacy</span>
            <span className="cursor-pointer transition-colors hover:text-foreground">Terms</span>
            <span className="cursor-pointer transition-colors hover:text-foreground">Status</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
