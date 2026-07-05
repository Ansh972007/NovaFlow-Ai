import client from "./client";

export const FLOW_TYPE_WORKFLOW = 10;

export async function getWorkflowsPage(params = {}) {
  const res = await client.get("/workflow", {
    params: { page: 1, limit: 50, ...params },
  });
  if (Array.isArray(res)) return { data: res, total: res.length };
  return { data: res?.data || [], total: res?.total || 0 };
}

export async function getWorkflowTemplates() {
  return client.get("/workflow/templates");
}

export async function getWorkflowInfo(id) {
  return client.get(`/workflow/info/${id}`);
}

export async function createWorkflow({ name, desc = "", templateId = "rag" }) {
  return client.post("/workflow", {
    name,
    desc,
    template_id: templateId,
  });
}

export async function updateWorkflow({ id, name, desc, graph }) {
  return client.put("/workflow", { id, name, desc, graph });
}

export async function setWorkflowStatus(id, status) {
  return client.post("/workflow/status", { id, status });
}

export async function deleteWorkflow(workflowId) {
  return client.post("/workflow/delete", { workflow_id: workflowId });
}

export async function runWorkflow(workflowId, input) {
  return client.post("/workflow/run", { workflow_id: workflowId, input });
}

export async function getOnlineWorkflows() {
  return client.get("/workflow/online");
}
