import client from "./client";

export const WORKSPACE_STORAGE_KEY = "nf_workspace_id";

export function getActiveWorkspaceId() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(WORKSPACE_STORAGE_KEY);
}

export function setActiveWorkspaceId(id) {
  if (typeof window === "undefined") return;
  localStorage.setItem(WORKSPACE_STORAGE_KEY, String(id));
}

export async function listWorkspaces() {
  return client.get("/workspaces");
}

export async function createWorkspace(name) {
  return client.post("/workspaces", { name });
}

export async function listWorkspaceMembers(workspaceId) {
  return client.get(`/workspaces/${workspaceId}/members`);
}

export async function inviteWorkspaceMember(workspaceId, user_name, role = "editor") {
  return client.post(`/workspaces/${workspaceId}/members`, { user_name, role });
}

export async function updateWorkspaceMemberRole(workspaceId, memberId, role) {
  return client.patch(`/workspaces/${workspaceId}/members/${memberId}/role`, { role });
}
