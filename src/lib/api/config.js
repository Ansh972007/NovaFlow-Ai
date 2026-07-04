/** NovaFlow API base URL (server + client) */
export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";
}

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "NovaFlow AI";
