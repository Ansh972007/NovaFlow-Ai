import { getApiBaseUrl } from "@/lib/api/config";

/** Server-side check — talks directly to the NovaFlow API (no browser CORS). */
export async function GET() {
  const apiUrl = getApiBaseUrl();

  try {
    const res = await fetch(`${apiUrl}/api/v1/user/public_key`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });

    if (res.ok) {
      return Response.json({ ok: true, apiUrl });
    }

    return Response.json(
      { ok: false, apiUrl, status: res.status },
      { status: 503 }
    );
  } catch {
    return Response.json(
      { ok: false, apiUrl, error: "unreachable" },
      { status: 503 }
    );
  }
}
