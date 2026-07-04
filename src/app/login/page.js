"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import Logo from "@/components/Logo";
import { login, register } from "@/lib/api/auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isRegister = searchParams.get("mode") === "register";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = isRegister
        ? await register(email, password)
        : await login(email, password);
      if (data?.access_token) {
        localStorage.setItem("nf_token", data.access_token);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo size="lg" />
        </div>

        <div className="rounded-2xl border border-nova-border bg-nova-surface p-8 shadow-sm">
          <h1 className="text-2xl font-bold tracking-tight">
            {isRegister ? "Create account" : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm text-nova-muted">
            {isRegister
              ? "Register to start using NovaFlow AI"
              : "Sign in to your workspace"}
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-foreground"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-nova-border bg-background px-4 py-2.5 text-sm outline-none focus:border-nova-primary focus:ring-2 focus:ring-indigo-500/20"
                placeholder="you@company.com"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-foreground"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete={isRegister ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-nova-border bg-background px-4 py-2.5 text-sm outline-none focus:border-nova-primary focus:ring-2 focus:ring-indigo-500/20"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="nova-gradient w-full rounded-lg py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              {loading
                ? "Please wait…"
                : isRegister
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-nova-muted">
            {isRegister ? "Already have an account?" : "New to NovaFlow AI?"}{" "}
            <Link
              href={isRegister ? "/login" : "/login?mode=register"}
              className="font-medium text-nova-primary hover:underline"
            >
              {isRegister ? "Sign in" : "Create account"}
            </Link>
          </p>
        </div>

        <p className="mt-6 text-center text-xs text-nova-muted">
          Backend must be running at{" "}
          <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">
            {process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001"}
          </code>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-full items-center justify-center text-nova-muted">
          Loading…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
