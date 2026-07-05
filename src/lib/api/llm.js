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
