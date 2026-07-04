/** Check NovaFlow API via Next.js server route (reliable local dev). */
export async function checkBackendHealth() {
  const res = await fetch("/api/health", { cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  return { ok: data.ok === true, apiUrl: data.apiUrl };
}
