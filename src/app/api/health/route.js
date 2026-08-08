import { getApiBaseUrl, getServerApiBaseUrl } from "@/lib/api/config";

const TIMEOUT_MS = 12_000;
const RETRIES = 3;

async function probe(url) {
  const res = await fetch(url, {
    cache: "no-store",
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!res.ok) return false;
  const data = await res.json().catch(() => ({}));
  return data.status_code === 200 || data.ok === true;
}

async function probeWithRetry(url) {
  for (let i = 0; i < RETRIES; i += 1) {
    try {
      if (await probe(url)) return true;
    } catch {
      /* retry */
    }
    if (i < RETRIES - 1) {
      await new Promise((r) => setTimeout(r, 800 * (i + 1)));
    }
  }
  return false;
}

/** Server-side check — NovaFlow API on port 3001 */
export async function GET() {
  const apiUrl = getServerApiBaseUrl().replace(/\/$/, "");
  const publicUrl = getApiBaseUrl().replace(/\/$/, "");

  const urls = [`${apiUrl}/health`];

  for (const url of urls) {
    if (await probeWithRetry(url)) {
      return Response.json({ ok: true, apiUrl: publicUrl, probe: url });
    }
  }

  return Response.json(
    {
      ok: false,
      apiUrl: publicUrl,
      hint: "Run .\\deploy\\start-backend.ps1 from novaflow-ai (NovaFlow stack, not Bisheng).",
    },
    { status: 503 }
  );
}
