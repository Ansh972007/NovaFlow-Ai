import client from "./client";

export async function listAgentTools() {
  return client.get("/agents/tools");
}

export async function runAgent(payload) {
  return client.post("/agents/run", payload);
}

export async function listSavedAgents() {
  return client.get("/agents");
}

export async function createSavedAgent(payload) {
  return client.post("/agents", payload);
}

export async function updateSavedAgent(id, payload) {
  return client.put(`/agents/${id}`, payload);
}

export async function deleteSavedAgent(id) {
  return client.delete(`/agents/${id}`);
}
