import Link from "next/link";
import Logo from "./Logo";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-nova-border bg-nova-surface/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo size="sm" />
        <nav className="hidden items-center gap-8 text-sm font-medium text-nova-muted md:flex">
          <Link href="#features" className="hover:text-foreground transition-colors">
            Features
          </Link>
          <Link href="#roadmap" className="hover:text-foreground transition-colors">
            Roadmap
          </Link>
          <Link href="/docs" className="hover:text-foreground transition-colors">
            Docs
          </Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="rounded-lg px-4 py-2 text-sm font-medium text-nova-muted hover:text-foreground transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/login?mode=register"
            className="nova-gradient rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:opacity-90 transition-opacity"
          >
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}
