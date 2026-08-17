import axios from "axios";
import { getClientBaseUrl } from "./client";

function getAuthHeaders() {
  const headers = {};
  if (typeof window !== "undefined") {
    try {
      const token = localStorage.getItem("nf_token");
      if (token) headers.Authorization = `Bearer ${token}`;
      const wid = localStorage.getItem("nf_workspace_id");
      if (wid) headers["X-Workspace-Id"] = wid;
    } catch (err) {
      console.error("Error accessing localStorage in getAuthHeaders:", err);
    }
  }
  return headers;
}

function unwrapResponse(res) {
  const data = res.data;
  if (data && typeof data === "object") {
    if (data.status_code === 200 || data.code === 200) {
      return data.data !== undefined ? data.data : data;
    }
    if (data.status_code && data.status_code !== 200) {
      throw new Error(data.status_message || data.detail || "Upload failed");
    }
  }
  if (res.status >= 200 && res.status < 300) {
    return data;
  }
  throw new Error(data?.status_message || data?.detail || "Upload failed");
}

/** Multipart upload (axios client defaults to JSON) */
export async function uploadMultipart(path, formData, { onProgress } = {}) {
  const normPath = path.startsWith("/") ? path : `/${path}`;
  const res = await axios.post(normPath, formData, {
    baseURL: getClientBaseUrl(),
    withCredentials: true,
    headers: getAuthHeaders(),
    timeout: 180000,
    onUploadProgress: onProgress,
  });
  return unwrapResponse(res);
}

