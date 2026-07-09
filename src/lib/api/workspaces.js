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

export async function ensureActiveWorkspace() {
  try {
    const data = await listWorkspaces();
    const items = data?.items || [];
    if (!items.length) {
      if (typeof window !== "undefined") {
        localStorage.removeItem(WORKSPACE_STORAGE_KEY);
      }
      return null;
    }
    const stored = getActiveWorkspaceId();
    const storedValid = stored && items.some((w) => String(w.id) === String(stored));
    if (stored && !storedValid && typeof window !== "undefined") {
      localStorage.removeItem(WORKSPACE_STORAGE_KEY);
    }
    const id = storedValid ? Number(stored) : data?.current_id || items[0]?.id;
    if (id) setActiveWorkspaceId(id);
    return id;
  } catch {
    if (typeof window !== "undefined") {
      localStorage.removeItem(WORKSPACE_STORAGE_KEY);
    }
    return null;
  }
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

export async function getWorkspaceQuotas(workspaceId) {
  return client.get(`/workspaces/${workspaceId}/quotas`);
}

export async function updateWorkspaceQuotas(workspaceId, payload) {
  return client.patch(`/workspaces/${workspaceId}/quotas`, payload);
}
