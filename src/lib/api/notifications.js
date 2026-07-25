import client from "./client";

export function getNotifications(workspaceId, params = {}) {
  return client.get("/notifications", { params: { workspace_id: workspaceId, ...params } });
}

export function getUnreadCount(workspaceId) {
  return client.get("/notifications/unread-count", { params: { workspace_id: workspaceId } });
}

export function markAsRead(id) {
  return client.post(`/notifications/${id}/read`);
}

export function markAllAsRead(workspaceId) {
  return client.post("/notifications/read-all", null, { params: { workspace_id: workspaceId } });
}

export function deleteNotification(id) {
  return client.delete(`/notifications/${id}`);
}

export function clearAllNotifications(workspaceId) {
  return client.delete("/notifications/clear-all", { params: { workspace_id: workspaceId } });
}

export function getPreferences() {
  return client.get("/notifications/preferences");
}

export function updatePreferences(body) {
  return client.patch("/notifications/preferences", body);
}
