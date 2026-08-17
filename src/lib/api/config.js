export function getApiBaseUrl() {
  // If explicitly configured in environment (e.g. Vercel -> Render backend URL), use it
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined") {
    if (window.location.port === "3000") {
      return `${window.location.protocol}//${window.location.hostname}:3001`;
    }
    if (window.location.hostname.includes("vercel.app")) {
      return "https://novaflow-ai.onrender.com";
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
    (process.env.VERCEL ? "https://novaflow-ai.onrender.com" : "http://localhost:3001")
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
  const [pathname, existingQuery] = normPath.split("?");

  const searchParams = new URLSearchParams(existingQuery || "");
  if (typeof window !== "undefined") {
    try {
      const token = localStorage.getItem("nf_token");
      if (token && !searchParams.has("t") && !searchParams.has("token")) {
        searchParams.set("t", token);
      }
      const wid = localStorage.getItem("nf_workspace_id");
      if (wid && !searchParams.has("workspace_id")) {
        searchParams.set("workspace_id", wid);
      }
    } catch (error) {
      console.error("Error accessing localStorage in getWsUrl:", error);
    }
  }
  const queryString = searchParams.toString();
  const finalPath = queryString ? `${pathname}?${queryString}` : pathname;

  // 1. Explicit WebSocket URL override
  if (process.env.NEXT_PUBLIC_WS_URL) {
    const baseWs = process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, "");
    return `${baseWs}${finalPath}`;
  }

  // 2. Derive directly from resolved API base URL (works across Vercel -> Render and local dev)
  const apiBase = getApiBaseUrl();
  try {
    const url = new URL(apiBase);
    const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${url.host}${finalPath}`;
  } catch {
    return `ws://127.0.0.1:3001${finalPath}`;
  }
}

