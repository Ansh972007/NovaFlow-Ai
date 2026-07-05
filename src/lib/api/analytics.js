import client from "./client";
import { getApiBaseUrl } from "./config";

export async function getAnalyticsSummary() {
  return client.get("/analytics/summary");
}

export async function getAnalyticsTimeseries(days = 7) {
  return client.get(`/analytics/timeseries?days=${days}`);
}

export async function getAnalyticsAssistants(days = 7) {
  return client.get(`/analytics/assistants?days=${days}`);
}

export async function getAssistantAnalytics(assistantId, days = 7) {
  return client.get(`/analytics/assistants/${assistantId}?days=${days}`);
}

export async function getAbRoutingAnalytics(days = 30) {
  return client.get(`/analytics/ab-routing?days=${days}`);
}

export async function getTeamMembers() {
  return client.get("/team/members");
}

export async function updateMemberRole(userId, role) {
  return client.patch(`/team/members/${userId}/role`, { role });
}

export async function downloadAuditExport(days = 30) {
  const token = typeof window !== "undefined" ? localStorage.getItem("nf_token") : null;
  const url = `${getApiBaseUrl().replace(/\/$/, "")}/api/v1/analytics/export?days=${days}`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.status_message || "Export failed");
  }
  const blob = await res.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `novaflow-audit-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}
