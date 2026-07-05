"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import LiveBackground from "@/components/LiveBackground";

function OAuthCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("Completing sign-in…");

  useEffect(() => {
    const token = searchParams.get("token");
    const error = searchParams.get("error");

    if (error) {
      setMessage(decodeURIComponent(error));
      return;
    }
    if (token) {
      localStorage.setItem("nf_token", token);
      router.replace("/chat");
      return;
    }
    setMessage("Missing OAuth token. Try signing in again.");
  }, [searchParams, router]);

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center px-4">
      <LiveBackground variant="light" showNetwork />
      <p className="relative z-10 max-w-md text-center text-sm text-neutral-600">{message}</p>
      {searchParams.get("error") && (
        <a href="/login" className="relative z-10 mt-6 text-sm font-semibold underline">
          Back to sign in
        </a>
      )}
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="relative flex min-h-screen items-center justify-center">
          <LiveBackground variant="light" showNetwork />
          <span className="relative z-10 text-neutral-500">Loading…</span>
        </div>
      }
    >
      <OAuthCallbackInner />
    </Suspense>
  );
}
