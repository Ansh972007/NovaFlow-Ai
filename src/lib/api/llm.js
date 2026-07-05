import client from "./client";

/** All LLM servers and models */
export async function getAllLlm() {
  return client.get("/llm");
}

/** Assistant default model configuration */
export async function getAssistantLlmConfig() {
  return client.get("/llm/assistant");
}

/** Knowledge embedding / model configuration */
export async function getKnowledgeLlmConfig() {
  return client.get("/llm/knowledge");
}

/** Admin: workspace model provider settings */
export async function getLlmSettings() {
  return client.get("/llm/settings");
}

export async function updateLlmSettings(payload) {
  return client.patch("/llm/settings", payload);
}

export async function getProviderTypes() {
  return client.get("/llm/provider-types");
}

export async function listLlmProviders() {
  return client.get("/llm/providers");
}

export async function createLlmProvider(payload) {
  return client.post("/llm/providers", payload);
}

export async function updateLlmProvider(id, payload) {
  return client.patch(`/llm/providers/${id}`, payload);
}

export async function deleteLlmProvider(id) {
  return client.delete(`/llm/providers/${id}`);
}

export async function activateLlmProvider(id) {
  return client.post(`/llm/providers/${id}/activate`);
}
