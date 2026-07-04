import axios from "axios";
import { getApiBaseUrl } from "./config";

const client = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

function formatApiError(error) {
  const apiUrl = getApiBaseUrl();

  if (!error.response) {
    if (error.code === "ECONNABORTED") {
      return "NovaFlow API timed out. Check that the backend is running and try again.";
    }
    return `Cannot reach the NovaFlow API at ${apiUrl}. Start the NovaFlow backend, then refresh this page.`;
  }

  const status = error.response.status;
  const data = error.response.data;

  if (status === 500 || status === 502 || status === 503) {
    return "NovaFlow API is temporarily unavailable. Make sure the backend is running on port 3001.";
  }

  if (data?.status_message) {
    return data.status_message;
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
  (error) => Promise.reject(new Error(formatApiError(error)))
);

export default client;
