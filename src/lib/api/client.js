import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

function formatApiError(error) {
  if (!error.response) {
    return "Cannot reach the backend. Start Bisheng Docker on port 3001, then try again.";
  }

  const status = error.response.status;
  const data = error.response.data;

  if (status === 500 || status === 502 || status === 503) {
    return "Backend server is unavailable. Run: docker compose -p bisheng up -d";
  }

  if (data?.status_message) {
    return data.status_message;
  }

  if (typeof data === "string" && data.includes("Internal Server Error")) {
    return "Backend server is unavailable. Please start the API on port 3001.";
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
