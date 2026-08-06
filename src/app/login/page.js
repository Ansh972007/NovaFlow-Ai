"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import AuthShowcasePanel from "@/components/AuthShowcasePanel";
import AuthFormPanel from "@/components/AuthFormPanel";
import LiveBackground from "@/components/LiveBackground";
import CursorGlow from "@/components/CursorGlow";
import { confirmPasswordReset, getLdapStatus, getLoginMode, login, register, requestPasswordReset } from "@/lib/api/auth";
import { checkBackendHealth } from "@/lib/api/health";
import { getOAuthProviders } from "@/lib/api/oauth";
import { getSamlStatus } from "@/lib/api/saml";
import PasswordResetPanel from "@/components/PasswordResetPanel";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isRegister = searchParams.get("mode") === "register";
  const nextPath = useMemo(() => {
    const next = searchParams.get("next") || "/chat";
    return next.startsWith("/") && !next.startsWith("//") ? next : "/chat";
  }, [searchParams]);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [backendOk, setBackendOk] = useState(null);
  const [checkingBackend, setCheckingBackend] = useState(false);
  const [focused, setFocused] = useState(null);
  const [greeting, setGreeting] = useState(0);
  const [oauthProviders, setOauthProviders] = useState([]);
  const [ldapEnabled, setLdapEnabled] = useState(false);
  const [samlEnabled, setSamlEnabled] = useState(false);
  const [passwordLogin, setPasswordLogin] = useState(false);
  const [gmailOnly, setGmailOnly] = useState(true);
  const [resetMode, setResetMode] = useState(false);

  async function probeBackend() {
    setCheckingBackend(true);
    try {
      const { ok } = await checkBackendHealth();
      setBackendOk(ok !== false);
    } catch {
      setBackendOk(true);
    } finally {
      setCheckingBackend(false);
    }
  }

  useEffect(() => {
    probeBackend();
    getOAuthProviders()
      .then((list) => setOauthProviders(Array.isArray(list) ? list : []))
      .catch(() => setOauthProviders([]));
    getLdapStatus()
      .then((s) => setLdapEnabled(!!s?.enabled))
      .catch(() => setLdapEnabled(false));
    getSamlStatus()
      .then((s) => setSamlEnabled(!!s?.enabled))
      .catch(() => setSamlEnabled(false));
    getLoginMode()
      .then((mode) => {
        setPasswordLogin(!!mode?.password_login);
        setGmailOnly(!!mode?.gmail_only);
      })
      .catch(() => {
        setPasswordLogin(false);
        setGmailOnly(true);
      });
  }, []);

  useEffect(() => {
    const inviteToken = searchParams.get("invite_token");
    const token = typeof window !== "undefined" ? localStorage.getItem("nf_token") : null;
    if (inviteToken && token) {
      import("@/lib/api/workspaces").then(({ acceptWorkspaceInvite }) => {
        acceptWorkspaceInvite(inviteToken)
          .then((res) => {
            if (res && res.workspace_id) {
              localStorage.setItem("nf_workspace_id", String(res.workspace_id));
            }
            router.push("/chat");
          })
          .catch((err) => {
            setError(err.message || "Failed to accept invite");
          });
      });
    }
  }, [searchParams, router]);

  const formProgress = useMemo(() => {
    let p = 0;
    const idOk = isRegister ? email.includes("@") : email.trim().length >= 1;
    if (idOk) p += 34;
    if (password.length >= 6) p += 33;
    if (!isRegister || (confirmPassword && confirmPassword === password)) p += 33;
    return Math.min(100, p);
  }, [email, password, confirmPassword, isRegister]);

  function switchMode(registerMode) {
    const inviteToken = searchParams.get("invite_token");
    const next = searchParams.get("next");
    const params = new URLSearchParams();
    if (registerMode) params.set("mode", "register");
    if (inviteToken) params.set("invite_token", inviteToken);
    if (next) params.set("next", next);
    const qs = params.toString();
    router.replace(qs ? `/login?${qs}` : "/login");
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
      const name = email.trim();
      const data = isRegister
        ? await register(name, password)
        : await login(name, password);

      const inviteToken = searchParams.get("invite_token");
      if (inviteToken) {
        try {
          const { acceptWorkspaceInvite } = await import("@/lib/api/workspaces");
          const res = await acceptWorkspaceInvite(inviteToken);
          if (res && res.workspace_id) {
            localStorage.setItem("nf_workspace_id", String(res.workspace_id));
          }
        } catch (inviteErr) {
          console.error("Failed to accept invite:", inviteErr);
        }
      }

      setGreeting((g) => g + 1);
      await new Promise((resolve) => setTimeout(resolve, 1400));
      if (data?.must_change_password) {
        router.push("/settings?tab=security&must_change=1");
      } else {
        router.push(nextPath);
      }
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  if (resetMode) {
    return (
      <div className="relative min-h-screen">
        <LiveBackground variant="light" showNetwork mouseTracking className="fixed inset-0" />
        <CursorGlow />
        <PasswordResetPanel
          onRequestCode={requestPasswordReset}
          onConfirm={confirmPasswordReset}
          onBack={() => setResetMode(false)}
        />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      <LiveBackground variant="light" showNetwork mouseTracking className="fixed inset-0" />
      <CursorGlow />

      <div className="relative grid min-h-screen lg:grid-cols-2">
        <AuthShowcasePanel isRegister={isRegister} greeting={greeting} />
        <AuthFormPanel
          isRegister={isRegister}
          email={email}
          setEmail={setEmail}
          password={password}
          setPassword={setPassword}
          confirmPassword={confirmPassword}
          setConfirmPassword={setConfirmPassword}
          showPassword={showPassword}
          setShowPassword={setShowPassword}
          loading={loading}
          error={error}
          backendOk={backendOk}
          checkingBackend={checkingBackend}
          onRetryBackend={probeBackend}
          focused={focused}
          setFocused={setFocused}
          formProgress={formProgress}
          switchMode={switchMode}
          handleSubmit={handleSubmit}
          oauthProviders={oauthProviders}
          ldapEnabled={ldapEnabled}
          samlEnabled={samlEnabled}
          passwordLogin={passwordLogin}
          gmailOnly={gmailOnly}
          onForgotPassword={() => setResetMode(true)}
        />
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="relative flex min-h-screen items-center justify-center">
          <LiveBackground variant="light" showNetwork />
          <span className="relative z-10 text-muted">Loading…</span>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
