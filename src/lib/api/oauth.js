import { getApiBaseUrl } from "./config";
import client from "./client";

export async function getOAuthProviders() {
  return client.get("/auth/oauth/providers");
}

export function startOAuthLogin(provider) {
  const base = getApiBaseUrl().replace(/\/$/, "");
  window.location.href = `${base}/api/v1/auth/oauth/${provider}/start`;
}
