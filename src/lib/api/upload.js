import axios from "axios";

function getAuthHeaders() {
  const headers = {};
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("nf_token");
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

function unwrapResponse(res) {
  if (res.data?.status_code === 200) return res.data.data;
  throw new Error(res.data?.status_message || "Upload failed");
}

/** Multipart upload (axios client defaults to JSON) */
export async function uploadMultipart(path, formData, { onProgress } = {}) {
  const res = await axios.post(path, formData, {
    baseURL: "/api/v1",
    withCredentials: true,
    headers: getAuthHeaders(),
    timeout: 120000,
    onUploadProgress: onProgress,
  });
  return unwrapResponse(res);
}
