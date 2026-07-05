/** NovaFlow API base URL (browser) */
export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";
}

/** Server-side probe target — uses Docker internal hostname when set */
export function getServerApiBaseUrl() {
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:3001"
  );
}

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "NovaFlow AI";

/** WebSocket query string with auth token and active workspace */
export function getWsQueryString() {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams();
  const token = localStorage.getItem("nf_token");
  if (token) params.set("t", token);
  const wid = localStorage.getItem("nf_workspace_id");
  if (wid) params.set("workspace_id", wid);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
