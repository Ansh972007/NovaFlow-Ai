"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Logo from "@/components/Logo";

export default function PasswordResetPanel({ onRequestCode, onConfirm, onBack }) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [step, setStep] = useState("email");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendCode(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onRequestCode(email.trim());
      setMessage("If an account matches this email, we sent a verification code.");
      setStep("reset");
    } catch (err) {
      setError(err.message || "Could not send verification code");
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(event) {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await onConfirm(email.trim(), code.trim(), newPassword);
      setMessage("Password reset successfully. You can now sign in.");
      setStep("done");
    } catch (err) {
      setError(err.message || "Password reset failed");
    } finally {
      setBusy(false);
    }
  }

  const inputClass = "mt-2 w-full rounded-xl border border-border bg-white px-4 py-3 text-sm outline-none transition focus:border-foreground";
  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10 sm:px-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative z-10 w-full max-w-[460px]">
        <Logo size="md" />
        <div className="mt-8 rounded-[1.35rem] border border-border bg-white/95 p-8 shadow-[0_40px_100px_rgba(0,0,0,0.1)] backdrop-blur-xl sm:p-10">
          <button type="button" onClick={onBack} className="text-sm text-muted hover:text-foreground">← Back to sign in</button>
          <h1 className="mt-6 font-serif text-3xl tracking-tight">Reset password</h1>
          <p className="mt-2 text-sm text-muted">We’ll send a six-digit verification code to your email.</p>

          {message && <p className="mt-5 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{message}</p>}
          {error && <p className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}

          {step === "email" && (
            <form onSubmit={sendCode} className="mt-7 space-y-5">
              <label className="block text-sm font-medium">Email address
                <input className={inputClass} type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="you@company.com" required />
              </label>
              <button disabled={busy} className="auth-submit-btn w-full rounded-full py-4 text-base font-semibold">{busy ? "Sending…" : "Send verification code"}</button>
            </form>
          )}

          {step === "reset" && (
            <form onSubmit={resetPassword} className="mt-7 space-y-5">
              <label className="block text-sm font-medium">Verification code
                <input className={inputClass} inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} autoComplete="one-time-code" placeholder="123456" required />
              </label>
              <label className="block text-sm font-medium">New password
                <input className={inputClass} type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} autoComplete="new-password" required />
              </label>
              <label className="block text-sm font-medium">Confirm new password
                <input className={inputClass} type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} autoComplete="new-password" required />
              </label>
              <button disabled={busy} className="auth-submit-btn w-full rounded-full py-4 text-base font-semibold">{busy ? "Resetting…" : "Reset password"}</button>
              <button type="button" disabled={busy} onClick={() => setStep("email")} className="w-full text-sm text-muted hover:text-foreground">Use a different email</button>
            </form>
          )}

          {step === "done" && <button type="button" onClick={onBack} className="auth-submit-btn mt-7 w-full rounded-full py-4 text-base font-semibold">Go to sign in</button>}
        </div>
      </motion.div>
    </div>
  );
}
