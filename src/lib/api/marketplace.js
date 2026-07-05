import client from "./client";

export async function listMarketplaceWorkflows() {
  return client.get("/marketplace/workflows");
}

export async function cloneMarketplaceWorkflow(workflowId) {
  return client.post(`/marketplace/workflows/${workflowId}/clone`);
}

export async function setWorkflowPublic(workflowId, isPublic) {
  return client.post(`/workflow/${workflowId}/share`, { is_public: isPublic });
}
