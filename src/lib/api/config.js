export function getApiBaseUrl() {
  // If explicitly configured in environment (e.g. Vercel -> Render backend URL), use it
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined") {
    if (window.location.port === "3000") {
      return `${window.location.protocol}//${window.location.hostname}:3001`;
    }
    if (window.location.origin) {
      return window.location.origin;
    }
  }
  return "http://127.0.0.1:3001";
}

/** Server-side probe target — uses Docker internal hostname when set */
export function getServerApiBaseUrl() {
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:3001"
  ).replace(/\/+$/, "");
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
  const normPath = path.startsWith("/") ? path : `/${path}`;

  // 1. Explicit WebSocket URL override
  if (process.env.NEXT_PUBLIC_WS_URL) {
    const baseWs = process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, "");
    return `${baseWs}${normPath}${getWsQueryString()}`;
  }

  // 2. Derive from configured public API URL (e.g. https://api.onrender.com -> wss://api.onrender.com)
  if (process.env.NEXT_PUBLIC_API_URL) {
    try {
      const url = new URL(process.env.NEXT_PUBLIC_API_URL);
      const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
      return `${wsProtocol}//${url.host}${normPath}${getWsQueryString()}`;
    } catch {
      // fallback to standard resolution
    }
  }

  // 3. Browser runtime detection (handles localhost:3000 -> localhost:3001 and relative origins)
  let host = "";
  let protocol = "ws:";
  if (typeof window !== "undefined") {
    protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    host = window.location.port === "3000" ? `${window.location.hostname}:3001` : window.location.host;
  } else {
    const apiUrl = getApiBaseUrl();
    try {
      const url = new URL(apiUrl);
      protocol = url.protocol === "https:" ? "wss:" : "ws:";
      host = url.host;
    } catch {
      host = "127.0.0.1:3001";
    }
  }
  return `${protocol}//${host}${normPath}${getWsQueryString()}`;
}

