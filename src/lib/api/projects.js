import client from "./client";

export async function listProjects() {
  return client.get("/projects");
}

export async function getProject(id) {
  return client.get(`/projects/${id}`);
}

export async function createProject(payload) {
  return client.post("/projects", payload);
}

export async function updateProject(id, payload) {
  return client.patch(`/projects/${id}`, payload);
}

export async function deleteProject(id) {
  return client.delete(`/projects/${id}`);
}

export async function runProjectWorkflow(projectId, workflowId, payload) {
  return client.post(`/projects/${projectId}/run/${workflowId}`, payload);
}
