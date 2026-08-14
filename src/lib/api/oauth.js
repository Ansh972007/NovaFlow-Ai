import { getApiBaseUrl } from "./config";
import client from "./client";

export async function getOAuthProviders() {
  try {
    const res = await client.get("/auth/oauth/providers");
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.data)) return res.data;
    if (Array.isArray(res?.data?.data)) return res.data.data;
    return [];
  } catch {
    try {
      const base = getApiBaseUrl().replace(/\/+$/, "");
      const direct = await fetch(`${base}/api/v1/auth/oauth/providers`, { cache: "no-store" });
      const json = await direct.json();
      if (Array.isArray(json)) return json;
      if (Array.isArray(json?.data)) return json.data;
      return [];
    } catch {
      return [];
    }
  }
}

export function startOAuthLogin(provider) {
  const base = getApiBaseUrl().replace(/\/+$/, "");
  const returnTo = typeof window !== "undefined" && window.location?.origin ? window.location.origin : "";
  const query = returnTo ? `?return_to=${encodeURIComponent(returnTo)}` : "";
  window.location.href = `${base}/api/v1/auth/oauth/${provider}/start${query}`;
}

