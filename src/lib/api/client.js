import axios from "axios";
import { getApiBaseUrl } from "./config";

const client = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  timeout: 60000,
});

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
  (error) => {
    const status = error.response?.status;
    if (typeof window !== "undefined") {
      const path = window.location?.pathname || "";
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
        try {
          localStorage.removeItem("nf_token");
          localStorage.removeItem("nf_workspace_id");
        } catch {
          /* ignore */
        }
        if (status === 401) {
          window.location.assign(`/login?next=${encodeURIComponent(path)}`);
        }
      }
    }
    return Promise.reject(new Error(formatApiError(error)));
  }
);

export default client;
