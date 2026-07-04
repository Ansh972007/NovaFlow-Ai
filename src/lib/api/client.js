import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.response.use(
  (response) => {
    if (response.data?.status_code === 200) {
      return response.data.data;
    }
    const message =
      response.data?.status_message || "Request failed";
    return Promise.reject(new Error(message));
  },
  (error) => {
    const message =
      error.response?.data?.status_message ||
      error.message ||
      "Network error";
    return Promise.reject(new Error(message));
  }
);

export default client;
