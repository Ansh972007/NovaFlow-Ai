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

export async function createWorkspace(name, options = {}) {
  return client.post("/workspaces", {
    name,
    workspace_type: options.workspace_type || options.type || "team",
    region: options.region || "global",
    timezone: options.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    language: options.language || "en",
    create_default_team: options.create_default_team !== false,
  });
}

export async function updateWorkspace(workspaceId, payload) {
  return client.patch(`/workspaces/${workspaceId}`, payload);
}

export async function listWorkspaceMembers(workspaceId) {
  return client.get(`/workspaces/${workspaceId}/members`);
}

export async function inviteWorkspaceMember(workspaceId, payload) {
  if (typeof payload === "string") {
    return client.post(`/workspaces/${workspaceId}/members`, { user_name: payload, role: "editor" });
  }
  return client.post(`/workspaces/${workspaceId}/members`, payload);
}

export async function updateWorkspaceMemberRole(workspaceId, memberId, role) {
  return client.patch(`/workspaces/${workspaceId}/members/${memberId}/role`, { role });
}

export async function listWorkspaceInvites(workspaceId) {
  return client.get(`/workspaces/${workspaceId}/invites`);
}

export async function revokeWorkspaceInvite(workspaceId, inviteId) {
  return client.delete(`/workspaces/${workspaceId}/invites/${inviteId}`);
}

export async function acceptWorkspaceInvite(token) {
  return client.post("/workspaces/invites/accept", { token });
}

export async function listWorkspaceTeams(workspaceId) {
  return client.get(`/workspaces/${workspaceId}/teams`);
}

export async function createWorkspaceTeam(workspaceId, payload) {
  return client.post(`/workspaces/${workspaceId}/teams`, payload);
}

export async function getWorkspaceQuotas(workspaceId) {
  return client.get(`/workspaces/${workspaceId}/quotas`);
}

export async function updateWorkspaceQuotas(workspaceId, payload) {
  return client.patch(`/workspaces/${workspaceId}/quotas`, payload);
}
