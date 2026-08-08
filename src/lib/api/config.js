export function getApiBaseUrl() {
  if (typeof window !== "undefined") {
    if (window.location.port === "3000") {
      return `${window.location.protocol}//${window.location.hostname}:3001`;
    }
    if (window.location.origin) {
      return window.location.origin;
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3001";
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
  try {
    const token = localStorage.getItem("nf_token");
    if (token) params.set("t", token);
    const wid = localStorage.getItem("nf_workspace_id");
    if (wid) params.set("workspace_id", wid);
  } catch (error) {
    console.error("Error accessing localStorage in getWsQueryString:", error);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

/** Centralized dynamic WebSocket URL builder */
export function getWsUrl(path) {
  let host = "";
  let protocol = "ws:";
  if (typeof window !== "undefined") {
    protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    host = window.location.port === "3000" ? `${window.location.hostname}:3001` : window.location.host;
  } else {
    const apiUrl = getApiBaseUrl();
    const url = new URL(apiUrl);
    protocol = url.protocol === "https:" ? "wss:" : "ws:";
    host = url.host;
  }
  return `${protocol}//${host}${path}${getWsQueryString()}`;
}
