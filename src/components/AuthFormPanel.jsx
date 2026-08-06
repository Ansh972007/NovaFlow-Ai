"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Logo from "@/components/Logo";
import Magnetic from "@/components/Magnetic";
import { startOAuthLogin } from "@/lib/api/oauth";
import { startSamlLogin } from "@/lib/api/saml";

const ease = [0.16, 1, 0.3, 1];

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
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: i < score ? 1 : 0.3 }}
            className={`h-1 flex-1 origin-left rounded-full ${i < score ? colors[score - 1] : "bg-surface"}`}
          />
        ))}
      </div>
      <p className="mt-1.5 text-[11px] text-muted">
        Strength: <span className="font-medium text-foreground">{labels[Math.max(0, score - 1)]}</span>
      </p>
    </motion.div>
  );
}

function AuthInput({ id, label, type, value, onChange, onFocus, onBlur, focused, placeholder, autoComplete, trailing }) {
  return (
    <motion.div
      animate={{ scale: focused ? 1.015 : 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className="relative"
    >
      <label
        htmlFor={id}
        className={`mb-2 block text-sm font-medium transition-colors ${focused ? "text-foreground" : "text-muted"}`}
      >
        {label}
      </label>
      <div className="relative">
        <motion.div
          animate={{ opacity: focused ? 1 : 0 }}
          className="pointer-events-none absolute -inset-0.5 rounded-[0.9rem] bg-gradient-to-r from-black/10 via-black/5 to-black/10 blur-sm"
        />
        <input
          id={id}
          type={type}
          required
          autoComplete={autoComplete}
          value={value}
          onChange={onChange}
          onFocus={onFocus}
          onBlur={onBlur}
          placeholder={placeholder}
          suppressHydrationWarning
          className={`input-field input-field-glow relative w-full transition-all ${
            focused ? "border-foreground bg-white shadow-[0_8px_30px_rgba(0,0,0,0.06)]" : ""
          } ${trailing ? "pr-14" : ""}`}
        />
        {trailing}
      </div>
    </motion.div>
  );
}

export default function AuthFormPanel({
  isRegister,
  email,
  setEmail,
  password,
  setPassword,
  confirmPassword,
  setConfirmPassword,
  showPassword,
  setShowPassword,
  loading,
  error,
  backendOk,
  checkingBackend,
  onRetryBackend,
  focused,
  setFocused,
  formProgress,
  switchMode,
  handleSubmit,
  oauthProviders = [],
  ldapEnabled = false,
  samlEnabled = false,
  passwordLogin = false,
  gmailOnly = true,
  onForgotPassword,
}) {
  const [clientReady, setClientReady] = useState(false);
  const [isForgot, setIsForgot] = useState(false);
  const [forgotStep, setForgotStep] = useState(1);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotCode, setForgotCode] = useState("");
  const [forgotNewPassword, setForgotNewPassword] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState("");
  const [forgotMsg, setForgotMsg] = useState("");

  useEffect(() => {
    setClientReady(true);
  }, []);

  async function handleSendResetCode(e) {
    e.preventDefault();
    setForgotError("");
    setForgotMsg("");
    if (!forgotEmail.trim()) {
      setForgotError("Email address is required");
      return;
    }
    setForgotLoading(true);
    try {
      const { requestPasswordReset } = await import("@/lib/api/auth");
      await requestPasswordReset(forgotEmail.trim());
      setForgotMsg("If an account matches, a 6-digit verification code has been sent.");
      setForgotStep(2);
    } catch (err) {
      setForgotError(err.message || "Failed to send reset code");
    } finally {
      setForgotLoading(false);
    }
  }

  async function handleConfirmReset(e) {
    e.preventDefault();
    setForgotError("");
    setForgotMsg("");
    if (!forgotCode.trim() || forgotCode.trim().length !== 6) {
      setForgotError("Please enter the 6-digit verification code");
      return;
    }
    if (!forgotNewPassword.trim() || forgotNewPassword.trim().length < 6) {
      setForgotError("Password must be at least 6 characters");
      return;
    }
    setForgotLoading(true);
    try {
      const { confirmPasswordReset } = await import("@/lib/api/auth");
      await confirmPasswordReset(forgotEmail.trim(), forgotCode.trim(), forgotNewPassword.trim());
      setForgotMsg("Password reset successfully. You can now sign in.");
      setTimeout(() => {
        setIsForgot(false);
        setForgotStep(1);
        setForgotEmail("");
        setForgotCode("");
        setForgotNewPassword("");
        setForgotMsg("");
        setForgotError("");
      }, 3000);
    } catch (err) {
      setForgotError(err.message || "Failed to reset password");
    } finally {
      setForgotLoading(false);
    }
  }

  const showPasswordForm = passwordLogin || ldapEnabled;
  const showOAuth = oauthProviders.length > 0 || samlEnabled;
  const googleProvider = oauthProviders.find((p) => p.id === "google");

  if (!clientReady) {
    return (
      <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-10 sm:px-8">
        <div className="relative z-10 w-full max-w-[460px]">
          <div className="gradient-border shadow-[0_40px_100px_rgba(0,0,0,0.1)]">
            <div className="relative min-h-[520px] overflow-hidden rounded-[1.35rem] bg-white/90 p-8 backdrop-blur-xl sm:p-10">
              <div className="animate-pulse space-y-6" aria-hidden>
                <div className="h-1 rounded-full bg-surface" />
                <div className="h-11 rounded-full bg-surface" />
                <div className="h-8 w-2/3 rounded-lg bg-surface" />
                <div className="h-12 rounded-xl bg-surface" />
                <div className="h-12 rounded-xl bg-surface" />
                <div className="h-14 rounded-full bg-surface" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-10 sm:px-8">
      <div className="relative z-10 mb-8 w-full max-w-[460px] lg:hidden">
        <Logo size="md" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease }}
        className="relative z-10 w-full max-w-[460px]"
      >
        <Link
          href="/"
          className="group mb-8 inline-flex items-center gap-2 text-sm text-muted transition-colors hover:text-foreground"
        >
          <span className="transition-transform group-hover:-translate-x-1">←</span>
          Back to home
        </Link>

        {backendOk === false && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 rounded-xl border border-amber-200 bg-amber-50/95 px-4 py-3 text-sm text-amber-900 backdrop-blur-sm"
          >
            <p className="font-medium">NovaFlow API is offline</p>
            <p className="mt-1 text-xs text-amber-800/90">
              Run <code className="rounded bg-amber-100 px-1">.\deploy\start-backend.ps1</code> from the{" "}
              <code className="rounded bg-amber-100 px-1">novaflow-ai</code> folder. Set{" "}
              <code className="rounded bg-amber-100 px-1">NOVAFLOW_ADMIN_PASSWORD</code> before first boot.
            </p>
            <button
              type="button"
              onClick={onRetryBackend}
              disabled={checkingBackend}
              className="mt-3 rounded-full border border-amber-300 bg-white px-4 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-50 disabled:opacity-50"
            >
              {checkingBackend ? "Checking…" : "Retry connection"}
            </button>
          </motion.div>
        )}

        <div className="gradient-border shadow-[0_40px_100px_rgba(0,0,0,0.1)]">
          <div className="relative overflow-hidden rounded-[1.35rem] bg-white/90 p-8 backdrop-blur-xl sm:p-10">
            {!isForgot && showPasswordForm && (
              <div className="mb-6 h-1 overflow-hidden rounded-full bg-surface">
                <motion.div
                  animate={{ width: `${formProgress}%` }}
                  transition={{ type: "spring", stiffness: 120, damping: 20 }}
                  className="h-full rounded-full bg-black"
                />
              </div>
            )}

            {!isForgot && showPasswordForm && passwordLogin && (
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
                {[
                  { mode: false, label: "Sign in" },
                  { mode: true, label: "Sign up" },
                ].map(({ mode, label }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => switchMode(mode)}
                    className={`relative z-10 flex-1 rounded-full py-3 text-sm font-semibold transition-colors ${
                      isRegister === mode ? "text-white" : "text-muted hover:text-foreground"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            <AnimatePresence mode="wait">
              {!isForgot ? (
                <motion.div
                  key={isRegister ? "register" : "login"}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -16 }}
                  transition={{ duration: 0.35, ease }}
                >
                  <div className="mt-8 flex items-center gap-3">
                    <motion.span
                      animate={{ rotate: 360 }}
                      transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                      className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-xs font-bold"
                    >
                      NF
                    </motion.span>
                    <div>
                      <h1 className="font-serif text-2xl tracking-tight sm:text-3xl">
                        {isRegister ? "Create account" : "Welcome back"}
                      </h1>
                      <p className="text-xs text-muted">
                        {gmailOnly
                          ? "Sign in with your Gmail account using Google"
                          : isRegister
                            ? "Free during beta · No card needed"
                            : "Access your AI workspace"}
                      </p>
                      {ldapEnabled && !isRegister && (
                        <span className="mt-2 inline-flex rounded-full bg-sky-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-sky-700">
                          LDAP sign-in enabled
                        </span>
                      )}
                    </div>
                  </div>

                  {showOAuth && !showPasswordForm && (
                    <div className="mt-8 space-y-4">
                      {error && (
                        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                          {error}
                        </p>
                      )}
                      {googleProvider && (
                        <Magnetic strength={0.28} className="w-full">
                          <button
                            type="button"
                            disabled={loading || backendOk === false}
                            onClick={() => startOAuthLogin("google")}
                            className="auth-submit-btn flex w-full items-center justify-center gap-2 rounded-full py-4 text-base font-semibold"
                          >
                            Continue with Google (Gmail)
                          </button>
                        </Magnetic>
                      )}
                      {samlEnabled && (
                        <button
                          type="button"
                          disabled={loading || backendOk === false}
                          onClick={startSamlLogin}
                          className="flex w-full items-center justify-center gap-2 rounded-full border border-border bg-white py-3 text-sm font-semibold transition hover:bg-surface disabled:opacity-50"
                        >
                          SAML SSO
                        </button>
                      )}
                      {!googleProvider && (
                        <p className="text-sm text-muted">
                          Google sign-in is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET on the server.
                        </p>
                      )}
                    </div>
                  )}

                  {showPasswordForm && (
                  <form onSubmit={handleSubmit} className="mt-8 space-y-6">
                    <AuthInput
                      id={isRegister ? "email" : "username"}
                      label={isRegister ? "Email address" : "Username"}
                      type={isRegister ? "email" : "text"}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onFocus={() => setFocused("email")}
                      onBlur={() => setFocused(null)}
                      focused={focused === "email"}
                      placeholder={isRegister ? "you@company.com" : ldapEnabled ? "username" : "you@gmail.com"}
                      autoComplete={isRegister ? "email" : "username"}
                    />
                    {!isRegister && passwordLogin && (
                      <p className="-mt-4 text-xs text-muted">
                        {gmailOnly
                          ? "Password sign-in requires a Gmail-linked account."
                          : "Use credentials issued by your administrator."}
                      </p>
                    )}

                    <div>
                      <AuthInput
                        id="password"
                        label="Password"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        onFocus={() => setFocused("password")}
                        onBlur={() => setFocused(null)}
                        focused={focused === "password"}
                        placeholder="••••••••"
                        autoComplete={isRegister ? "new-password" : "current-password"}
                        trailing={
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg px-2.5 py-1 text-[11px] font-semibold text-muted transition-all hover:bg-surface hover:text-foreground"
                          >
                            {showPassword ? "Hide" : "Show"}
                          </button>
                        }
                      />
                      {isRegister && <PasswordStrength password={password} />}
                    </div>

                    <AnimatePresence>
                      {isRegister && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                        >
                          <AuthInput
                            id="confirm"
                            label="Confirm password"
                            type={showPassword ? "text" : "password"}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            onFocus={() => setFocused("confirm")}
                            onBlur={() => setFocused(null)}
                            focused={focused === "confirm"}
                            placeholder="••••••••"
                            autoComplete="new-password"
                          />
                          {confirmPassword && confirmPassword !== password && (
                            <p className="mt-2 text-xs text-red-600">Passwords do not match</p>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {!isRegister && (
                      <div className="flex justify-end">
                        <button
                          type="button"
                          onClick={() => {
                            setIsForgot(true);
                            setForgotError("");
                            setForgotMsg("");
                          }}
                          className="text-xs text-muted transition-colors hover:text-foreground"
                        >
                          Forgot password?
                        </button>
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

                    <Magnetic strength={0.28} className="w-full">
                      <button
                        type="submit"
                        disabled={loading || backendOk === false}
                        className="auth-submit-btn w-full rounded-full py-4 text-base font-semibold"
                      >
                        {loading ? (
                          <span className="flex items-center justify-center gap-2">
                            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                            Authenticating…
                          </span>
                        ) : isRegister ? (
                          "Create account →"
                        ) : (
                          "Sign in →"
                        )}
                      </button>
                    </Magnetic>
                  </form>
                  )}

                  {showOAuth && showPasswordForm && (
                    <div className="mt-6">
                      <div className="relative mb-4">
                        <div className="absolute inset-0 flex items-center">
                          <div className="w-full border-t border-border" />
                        </div>
                        <div className="relative flex justify-center text-[11px] uppercase tracking-wide">
                          <span className="bg-white/90 px-3 text-muted">Or continue with</span>
                        </div>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {samlEnabled && (
                          <button
                            type="button"
                            disabled={loading || backendOk === false}
                            onClick={startSamlLogin}
                            className="flex items-center justify-center gap-2 rounded-full border border-border bg-white py-3 text-sm font-semibold transition hover:bg-surface disabled:opacity-50 sm:col-span-2"
                          >
                            SAML SSO
                          </button>
                        )}
                        {oauthProviders.map((provider) => (
                          <button
                            key={provider.id}
                            type="button"
                            disabled={loading || backendOk === false}
                            onClick={() => startOAuthLogin(provider.id)}
                            className="flex items-center justify-center gap-2 rounded-full border border-border bg-white py-3 text-sm font-semibold transition hover:bg-surface disabled:opacity-50"
                          >
                            {provider.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-6 flex flex-wrap gap-2">
                    {["Encrypted", gmailOnly ? "Gmail only" : "Secure"].map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-border bg-surface px-3 py-1 text-[10px] font-medium text-muted"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {passwordLogin && (
                  <p className="mt-6 text-center text-sm text-muted">
                    {isRegister ? "Already have an account?" : "New to NovaFlow?"}{" "}
                    <button
                      type="button"
                      onClick={() => switchMode(!isRegister)}
                      className="font-semibold text-foreground underline-offset-4 hover:underline"
                    >
                      {isRegister ? "Sign in" : "Create account"}
                    </button>
                  </p>
                  )}
                </motion.div>
              ) : (
                <motion.div
                  key="forgot"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -16 }}
                  transition={{ duration: 0.35, ease }}
                >
                  <div className="mt-8 flex items-center gap-3">
                    <motion.span
                      animate={{ rotate: 360 }}
                      transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                      className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-xs font-bold"
                    >
                      NF
                    </motion.span>
                    <div>
                      <h1 className="font-serif text-2xl tracking-tight sm:text-3xl">
                        Reset password
                      </h1>
                      <p className="text-xs text-muted">
                        Verification code will be sent to your email
                      </p>
                    </div>
                  </div>

                  {forgotStep === 1 ? (
                    <form onSubmit={handleSendResetCode} className="mt-8 space-y-6">
                      <AuthInput
                        id="forgot-email"
                        label="Email address"
                        type="email"
                        value={forgotEmail}
                        onChange={(e) => setForgotEmail(e.target.value)}
                        onFocus={() => setFocused("forgot-email")}
                        onBlur={() => setFocused(null)}
                        focused={focused === "forgot-email"}
                        placeholder="you@company.com"
                        autoComplete="email"
                      />

                      {forgotError && (
                        <motion.p
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                        >
                          {forgotError}
                        </motion.p>
                      )}

                      {forgotMsg && (
                        <motion.p
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"
                        >
                          {forgotMsg}
                        </motion.p>
                      )}

                      <Magnetic strength={0.28} className="w-full">
                        <button
                          type="submit"
                          disabled={forgotLoading}
                          className="auth-submit-btn w-full rounded-full py-4 text-base font-semibold"
                        >
                          {forgotLoading ? (
                            <span className="flex items-center justify-center gap-2">
                              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                              Sending code…
                            </span>
                          ) : (
                            "Send verification code →"
                          )}
                        </button>
                      </Magnetic>
                    </form>
                  ) : (
                    <form onSubmit={handleConfirmReset} className="mt-8 space-y-6">
                      <p className="text-sm text-muted">
                        We sent a code to <strong className="text-foreground">{forgotEmail}</strong>
                      </p>

                      <AuthInput
                        id="forgot-code"
                        label="Verification Code"
                        type="text"
                        value={forgotCode}
                        onChange={(e) => setForgotCode(e.target.value)}
                        onFocus={() => setFocused("forgot-code")}
                        onBlur={() => setFocused(null)}
                        focused={focused === "forgot-code"}
                        placeholder="000000"
                        autoComplete="off"
                      />

                      <div>
                        <AuthInput
                          id="forgot-new-password"
                          label="New Password"
                          type={showPassword ? "text" : "password"}
                          value={forgotNewPassword}
                          onChange={(e) => setForgotNewPassword(e.target.value)}
                          onFocus={() => setFocused("forgot-new-password")}
                          onBlur={() => setFocused(null)}
                          focused={focused === "forgot-new-password"}
                          placeholder="••••••••"
                          autoComplete="new-password"
                          trailing={
                            <button
                              type="button"
                              onClick={() => setShowPassword(!showPassword)}
                              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg px-2.5 py-1 text-[11px] font-semibold text-muted transition-all hover:bg-surface hover:text-foreground"
                            >
                              {showPassword ? "Hide" : "Show"}
                            </button>
                          }
                        />
                        <PasswordStrength password={forgotNewPassword} />
                      </div>

                      {forgotError && (
                        <motion.p
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                        >
                          {forgotError}
                        </motion.p>
                      )}

                      {forgotMsg && (
                        <motion.p
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"
                        >
                          {forgotMsg}
                        </motion.p>
                      )}

                      <Magnetic strength={0.28} className="w-full">
                        <button
                          type="submit"
                          disabled={forgotLoading}
                          className="auth-submit-btn w-full rounded-full py-4 text-base font-semibold"
                        >
                          {forgotLoading ? (
                            <span className="flex items-center justify-center gap-2">
                              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                              Resetting password…
                            </span>
                          ) : (
                            "Reset password →"
                          )}
                        </button>
                      </Magnetic>
                    </form>
                  )}

                  <p className="mt-6 text-center text-sm text-muted">
                    Remembered your password?{" "}
                    <button
                      type="button"
                      onClick={() => {
                        setIsForgot(false);
                        setForgotStep(1);
                        setForgotError("");
                        setForgotMsg("");
                      }}
                      className="font-semibold text-foreground underline-offset-4 hover:underline"
                    >
                      Sign in
                    </button>
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-8 text-center text-[11px] text-muted-light"
        >
          Trusted by teams building with AI · Enterprise-ready infrastructure
        </motion.p>
      </motion.div>
    </div>
  );
}
