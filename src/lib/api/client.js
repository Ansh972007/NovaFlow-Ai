import axios from "axios";
import { getApiBaseUrl } from "./config";

const client = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  timeout: 60000,
});

let refreshPromise = null;
let isRefreshing = false;
let tokenExpiryTime = null;
let refreshTimer = null;
const TOKEN_REFRESH_BUFFER = 5 * 60 * 1000; // Refresh 5 minutes before expiry

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
    // Calculate token expiry time (assuming 15 minutes default)
    const expiresIn = (data.expires_in || 15 * 60) * 1000;
    tokenExpiryTime = Date.now() + expiresIn;
    scheduleProactiveRefresh();
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
    tokenExpiryTime = null;
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
  } catch {
    /* ignore */
  }
}

function scheduleProactiveRefresh() {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }
  
  if (!tokenExpiryTime) {
    return;
  }
  
  const refreshDelay = Math.max(0, tokenExpiryTime - Date.now() - TOKEN_REFRESH_BUFFER);
  
  refreshTimer = setTimeout(async () => {
    try {
      console.log("Proactively refreshing access token...");
      await refreshAccessToken();
      console.log("Proactive token refresh successful");
    } catch (error) {
      console.error("Proactive token refresh failed:", error);
      // If proactive refresh fails, it will be handled reactively on next request
    }
  }, refreshDelay);
}

async function refreshAccessToken() {
  try {
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
  } catch (error) {
    console.error("Token refresh failed:", error);
    throw error;
  }
}

client.interceptors.request.use(async (config) => {
  if (typeof window !== "undefined") {
    try {
      // Proactive token refresh if token is about to expire
      if (tokenExpiryTime && Date.now() > tokenExpiryTime - TOKEN_REFRESH_BUFFER) {
        if (!isRefreshing) {
          try {
            console.log("Token expiring soon, refreshing proactively...");
            await refreshAccessToken();
          } catch (error) {
            console.error("Proactive refresh failed, will try reactive:", error);
          }
        }
      }
      
      const token = localStorage.getItem("nf_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      const wid = localStorage.getItem("nf_workspace_id");
      if (wid) {
        config.headers["X-Workspace-Id"] = wid;
      }
    } catch (error) {
      console.error("Error accessing localStorage in request interceptor:", error);
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

    // Retry logic for network errors and 5xx errors
    if (
      original &&
      !original._nfRetry &&
      !original._nfNetworkRetry &&
      (error.code === "ECONNABORTED" || error.code === "ECONNRESET" || 
       status === 502 || status === 503 || status === 504 || status === 429)
    ) {
      original._nfNetworkRetry = true;
      const retryCount = original._nfRetryCount || 0;
      const maxRetries = 3;
      
      if (retryCount < maxRetries) {
        original._nfRetryCount = retryCount + 1;
        const delay = Math.min(1000 * Math.pow(2, retryCount), 10000); // Exponential backoff, max 10s
        
        console.log(`Retrying request (attempt ${retryCount + 1}/${maxRetries}) after ${delay}ms...`);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        return client(original);
      }
    }

    // Auth error handling
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
      
      // If already refreshing, wait for the existing promise
      if (refreshPromise) {
        try {
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

      // Start new refresh process
      try {
        isRefreshing = true;
        refreshPromise = refreshAccessToken();
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
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    }

    if (typeof window !== "undefined") {
      try {
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
      } catch (error) {
        console.error("Error in response interceptor:", error);
      }
    }
    return Promise.reject(new Error(formatApiError(error)));
  }
);

export default client;
