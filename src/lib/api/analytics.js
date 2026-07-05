import client from "./client";

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

export async function getTeamMembers() {
  return client.get("/team/members");
}

export async function updateMemberRole(userId, role) {
  return client.patch(`/team/members/${userId}/role`, { role });
}
