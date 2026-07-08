import { getApiBaseUrl } from "./config";

/** Check NovaFlow API via Next.js server route (reliable local dev). */
export async function checkBackendHealth() {
  const apiUrl = getApiBaseUrl().replace(/\/$/, "");

  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const res = await fetch("/api/health", { cache: "no-store" });
      const data = await res.json().catch(() => ({}));
      if (data.ok === true) {
        return { ok: true, apiUrl: data.apiUrl || apiUrl };
      }
    } catch {
      /* retry */
    }

    // Fallback: browser can reach the API directly when the Next proxy is slow
    if (typeof window !== "undefined") {
      try {
        const direct = await fetch(`${apiUrl}/health`, {
          cache: "no-store",
          signal: AbortSignal.timeout(12_000),
        });
        const data = await direct.json().catch(() => ({}));
        if (data.status_code === 200 || data.data?.status === "ok") {
          return { ok: true, apiUrl };
        }
      } catch {
        /* retry */
      }
    }

    if (attempt < 2) {
      await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
    }
  }

  return { ok: false, apiUrl };
}
