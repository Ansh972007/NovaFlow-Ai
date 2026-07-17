import axios from "axios";
import { getApiBaseUrl } from "./config";

const client = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  timeout: 60000,
});

let refreshPromise = null;

function formatApiError(error) {
  const apiUrl = getApiBaseUrl();

  if (!error.response) {
    if (error.code === "ECONNABORTED") {
      return "NovaFlow API timed out. Check that the backend is running and try again.";
    }
    return `Cannot reach the NovaFlow API at ${apiUrl}. Start the NovaFlow backend (port 3001), then hard-refresh this page. If you are on Windows, use http://127.0.0.1:3001 instead of localhost.`;
  }

  const status = error.response.status;
  const data = error.response.data;

  if (status === 500 || status === 502 || status === 503) {
    return "NovaFlow API is temporarily unavailable. Make sure the backend is running on port 3001.";
  }

  if (data?.status_message) {
    return data.status_message;
  }

  if (data?.detail) {
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
  }

  if (typeof data === "string" && data.includes("Internal Server Error")) {
    return "NovaFlow API is unavailable. Please start the backend on port 3001.";
  }

  return error.message || `Request failed (${status})`;
}

export function storeAuthTokens(data) {
  if (typeof window === "undefined" || !data) return;
  if (data.access_token) {
    localStorage.setItem("nf_token", data.access_token);
  }
  if (data.refresh_token) {
    localStorage.setItem("nf_refresh_token", data.refresh_token);
  }
}

export function clearAuthTokens() {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem("nf_token");
    localStorage.removeItem("nf_refresh_token");
    localStorage.removeItem("nf_workspace_id");
  } catch {
    /* ignore */
  }
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem("nf_refresh_token");
  if (!refresh) {
    throw new Error("No refresh token");
  }
  const res = await axios.post(
    "/api/v1/user/refresh",
    { refresh_token: refresh },
    { headers: { "Content-Type": "application/json" }, timeout: 15000 }
  );
  const payload = res.data?.data || res.data;
  if (!payload?.access_token) {
    throw new Error("Refresh failed");
  }
  storeAuthTokens(payload);
  return payload.access_token;
}

client.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("nf_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const wid = localStorage.getItem("nf_workspace_id");
    if (wid) {
      config.headers["X-Workspace-Id"] = wid;
    }
  }
  return config;
});

client.interceptors.response.use(
  (response) => {
    if (response.data?.status_code === 200) {
      return response.data.data;
    }
    const message = response.data?.status_message || "Request failed";
    return Promise.reject(new Error(message));
  },
  async (error) => {
    const status = error.response?.status;
    const original = error.config;
    const path = typeof window !== "undefined" ? window.location?.pathname || "" : "";

    if (
      typeof window !== "undefined" &&
      status === 401 &&
      original &&
      !original._nfRetry &&
      !String(original.url || "").includes("/user/login") &&
      !String(original.url || "").includes("/user/refresh") &&
      !String(original.url || "").includes("/user/regist")
    ) {
      original._nfRetry = true;
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null;
          });
        }
        const newToken = await refreshPromise;
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return client(original);
      } catch {
        clearAuthTokens();
        if (!path.startsWith("/login") && !path.startsWith("/setup")) {
          window.location.assign(`/login?next=${encodeURIComponent(path)}`);
        }
        return Promise.reject(new Error(formatApiError(error)));
      }
    }

    if (typeof window !== "undefined") {
      const detail = error.response?.data?.detail || error.response?.data?.status_message || "";
      const staleWorkspace =
        status === 404 &&
        typeof detail === "string" &&
        detail.toLowerCase().includes("workspace");

      if (staleWorkspace) {
        try {
          localStorage.removeItem("nf_workspace_id");
        } catch {
          /* ignore */
        }
      }

      if ((status === 401 || status === 403) && !path.startsWith("/login") && !path.startsWith("/setup")) {
        if (status === 401) {
          clearAuthTokens();
          window.location.assign(`/login?next=${encodeURIComponent(path)}`);
        }
      }
    }
    return Promise.reject(new Error(formatApiError(error)));
  }
);

export default client;
