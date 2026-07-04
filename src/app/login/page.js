"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Logo from "@/components/Logo";
import CursorGlow from "@/components/CursorGlow";
import Magnetic from "@/components/Magnetic";
import LiveBackground from "@/components/LiveBackground";
import { login, register } from "@/lib/api/auth";
import client from "@/lib/api/client";

const ease = [0.16, 1, 0.3, 1];

const features = [
  { icon: "⚡", title: "Streaming chat", desc: "Real-time AI responses" },
  { icon: "📚", title: "Knowledge RAG", desc: "Ground answers in your docs" },
  { icon: "🔒", title: "Enterprise security", desc: "Roles, audit logs, SSO" },
];

function PasswordStrength({ password }) {
  if (!password) return null;
  const score =
    (password.length >= 8 ? 1 : 0) +
    (/[A-Z]/.test(password) ? 1 : 0) +
    (/[0-9]/.test(password) ? 1 : 0) +
    (/[^A-Za-z0-9]/.test(password) ? 1 : 0);
  const labels = ["Weak", "Fair", "Good", "Strong"];
  const colors = ["bg-red-400", "bg-amber-400", "bg-lime-500", "bg-green-500"];

  return (
    <div className="mt-2">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i < score ? colors[score - 1] : "bg-surface"
            }`}
          />
        ))}
      </div>
      <p className="mt-1 text-[11px] text-muted">
        Password strength: {labels[Math.max(0, score - 1)]}
      </p>
    </div>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isRegister = searchParams.get("mode") === "register";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [backendOk, setBackendOk] = useState(null);
  const [activeFeature, setActiveFeature] = useState(0);

  useEffect(() => {
    client
      .get("/user/public_key")
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveFeature((f) => (f + 1) % features.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  function switchMode(registerMode) {
    router.replace(registerMode ? "/login?mode=register" : "/login");
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (isRegister && password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (isRegister && password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);
    try {
      const data = isRegister
        ? await register(email, password)
        : await login(email, password);
      if (data?.access_token) {
        localStorage.setItem("nf_token", data.access_token);
      }
      router.push("/chat");
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative grid min-h-screen lg:grid-cols-2">
      <CursorGlow />
      {/* Left — dark live panel */}
      <div className="section-dark relative hidden flex-col justify-between overflow-hidden p-12 lg:flex">
        <LiveBackground variant="dark" showNetwork mouseTracking />
        <div className="relative z-10">
          <Logo variant="dark" size="md" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease }}
          className="relative z-10"
        >
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500 uppercase">
            {isRegister ? "Join NovaFlow" : "Welcome back"}
          </p>
          <h2 className="mt-4 font-serif text-5xl leading-[1.1] tracking-tight">
            {isRegister ? (
              <>
                Build your
                <br />
                <span className="italic text-neutral-400">AI workspace.</span>
              </>
            ) : (
              <>
                The professional
                <br />
                <span className="italic text-neutral-400">AI workspace.</span>
              </>
            )}
          </h2>
          <p className="mt-6 max-w-sm text-neutral-400">
            {isRegister
              ? "Create your account and start deploying AI assistants in minutes."
              : "Sign in to access chat, knowledge bases, and your team's AI applications."}
          </p>

          <div className="relative mt-12 h-28">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeFeature}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.4, ease }}
                className="absolute inset-0 rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-sm"
              >
                <span className="text-2xl">{features[activeFeature].icon}</span>
                <p className="mt-2 font-semibold">{features[activeFeature].title}</p>
                <p className="mt-1 text-sm text-neutral-400">
                  {features[activeFeature].desc}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="mt-4 flex gap-2">
            {features.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setActiveFeature(i)}
                className={`h-1 rounded-full transition-all ${
                  i === activeFeature ? "w-6 bg-white" : "w-2 bg-white/30"
                }`}
                aria-label={`Feature ${i + 1}`}
              />
            ))}
          </div>
        </motion.div>

        <p className="relative z-10 text-xs text-neutral-600">© NovaFlow AI</p>
      </div>

      {/* Right — form with live bg */}
      <div className="relative flex flex-col items-center justify-center px-4 py-12">
        <LiveBackground variant="light" showNetwork mouseTracking />
        <div className="noise pointer-events-none absolute inset-0" />

        <div className="relative z-10 mb-8 lg:hidden">
          <Logo size="md" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease }}
          className="relative z-10 w-full max-w-md"
        >
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-2 text-sm text-muted transition-colors hover:text-foreground"
          >
            ← Back to home
          </Link>

          {backendOk === false && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 rounded-xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm text-amber-900 backdrop-blur-sm"
            >
              Backend offline. Start Bisheng:{" "}
              <code className="text-xs">docker compose -p bisheng up -d</code>
            </motion.div>
          )}

          <div className="glass-card rounded-[1.5rem] p-8">
            {/* Tab switcher */}
            <div className="relative flex rounded-full bg-surface p-1">
              <motion.div
                layout
                className="auth-tab-active absolute top-1 bottom-1 rounded-full"
                style={{
                  width: "calc(50% - 4px)",
                  left: isRegister ? "calc(50% + 2px)" : "4px",
                }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
              <button
                type="button"
                onClick={() => switchMode(false)}
                className={`relative z-10 flex-1 rounded-full py-2.5 text-sm font-semibold transition-colors ${
                  !isRegister ? "text-white" : "text-muted"
                }`}
              >
                Sign in
              </button>
              <button
                type="button"
                onClick={() => switchMode(true)}
                className={`relative z-10 flex-1 rounded-full py-2.5 text-sm font-semibold transition-colors ${
                  isRegister ? "text-white" : "text-muted"
                }`}
              >
                Sign up
              </button>
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={isRegister ? "register" : "login"}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.3, ease }}
              >
                <h1 className="mt-8 font-serif text-3xl tracking-tight">
                  {isRegister ? "Create account" : "Welcome back"}
                </h1>
                <p className="mt-2 text-sm text-muted">
                  {isRegister
                    ? "Start building with NovaFlow AI — free during beta"
                    : "Enter your credentials to continue"}
                </p>

                <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                  <div>
                    <label htmlFor="email" className="text-sm font-medium">
                      Email address
                    </label>
                    <input
                      id="email"
                      type="email"
                      required
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="input-field input-field-glow mt-1.5"
                      placeholder="you@company.com"
                    />
                  </div>

                  <div>
                    <label htmlFor="password" className="text-sm font-medium">
                      Password
                    </label>
                    <div className="relative mt-1.5">
                      <input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        required
                        autoComplete={isRegister ? "new-password" : "current-password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="input-field input-field-glow pr-12"
                        placeholder="••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted transition-colors hover:text-foreground"
                      >
                        {showPassword ? "Hide" : "Show"}
                      </button>
                    </div>
                    {isRegister && <PasswordStrength password={password} />}
                  </div>

                  {isRegister && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                    >
                      <label htmlFor="confirm" className="text-sm font-medium">
                        Confirm password
                      </label>
                      <input
                        id="confirm"
                        type={showPassword ? "text" : "password"}
                        required
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="input-field input-field-glow mt-1.5"
                        placeholder="••••••••"
                      />
                    </motion.div>
                  )}

                  {!isRegister && (
                    <div className="flex justify-end">
                      <span className="cursor-pointer text-xs text-muted transition-colors hover:text-foreground">
                        Forgot password?
                      </span>
                    </div>
                  )}

                  {error && (
                    <motion.p
                      initial={{ opacity: 0, scale: 0.98 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                    >
                      {error}
                    </motion.p>
                  )}

                  <Magnetic strength={0.2} className="w-full">
                    <button
                      type="submit"
                      disabled={loading || backendOk === false}
                      className="btn-primary w-full disabled:opacity-50"
                    >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        Please wait…
                      </span>
                    ) : isRegister ? (
                      "Create account →"
                    ) : (
                      "Sign in →"
                    )}
                    </button>
                  </Magnetic>
                </form>

                {isRegister && (
                  <p className="mt-4 text-center text-[11px] text-muted-light">
                    By signing up you agree to our Terms and Privacy Policy.
                  </p>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="relative flex min-h-screen items-center justify-center">
          <LiveBackground variant="light" />
          <span className="relative z-10 text-muted">Loading…</span>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
