import { getApiBaseUrl, getServerApiBaseUrl } from "@/lib/api/config";

const TIMEOUT_MS = 10_000;

async function probe(url) {
  const res = await fetch(url, {
    cache: "no-store",
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!res.ok) return false;
  const data = await res.json().catch(() => ({}));
  return data.status_code === 200 || data.ok === true;
}

/** Server-side check — NovaFlow API on port 3001 */
export async function GET() {
  const apiUrl = getServerApiBaseUrl().replace(/\/$/, "");
  const publicUrl = getApiBaseUrl().replace(/\/$/, "");

  const urls = [
    `${apiUrl}/health`,
    `${apiUrl}/api/v1/user/public_key`,
  ];

  for (const url of urls) {
    try {
      if (await probe(url)) {
        return Response.json({ ok: true, apiUrl: publicUrl, probe: url });
      }
    } catch {
      /* try next */
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
