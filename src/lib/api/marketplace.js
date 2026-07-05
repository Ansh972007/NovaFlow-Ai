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

export async function rateMarketplaceWorkflow(workflowId, { score, comment = "" }) {
  return client.post(`/marketplace/workflows/${workflowId}/rate`, { score, comment });
}

export async function listWorkflowComments(workflowId) {
  return client.get(`/marketplace/workflows/${workflowId}/comments`);
}

export async function postWorkflowComment(workflowId, body) {
  return client.post(`/marketplace/workflows/${workflowId}/comments`, { body });
}
