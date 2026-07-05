import client from "./client";

/** Online assistants & workflows available for chat */
export async function getOnlineApps(params = {}) {
  return client.get("/chat/online", {
    params: { page: 1, limit: 50, ...params },
  });
}

/** All assistants (including offline — for empty online list) */
export async function getAssistants(params = {}) {
  const res = await client.get("/assistant", {
    params: { page: 1, limit: 50, ...params },
  });
  if (Array.isArray(res)) return res;
  return res?.data || [];
}

/** Paginated assistant list */
export async function getAssistantsPage(params = {}) {
  const res = await client.get("/assistant", {
    params: { page: 1, limit: 50, ...params },
  });
  if (Array.isArray(res)) return { data: res, total: res.length };
  return { data: res?.data || [], total: res?.total || 0 };
}

/** Assistant detail */
export async function getAssistantInfo(id) {
  return client.get(`/assistant/info/${id}`);
}

/** Create assistant */
export async function createAssistant({ name, prompt, logo = "" }) {
  return client.post("/assistant", { name, prompt, logo });
}

/** Update assistant (partial) */
export async function updateAssistant(data) {
  return client.put("/assistant", data);
}

/** Publish or unpublish assistant (status: 0 offline, 1 online) */
export async function setAssistantStatus(id, status) {
  return client.post("/assistant/status", { id, status });
}

/** Delete assistant */
export async function deleteAssistant(assistantId) {
  return client.post("/assistant/delete", { assistant_id: assistantId });
}

/** Link knowledge bases to assistant for RAG */
export async function setAssistantKnowledge(assistantId, knowledgeIds) {
  return client.post("/assistant/knowledge", {
    assistant_id: assistantId,
    knowledge_ids: knowledgeIds,
  });
}

/** Load message history for a session */
export async function getChatMessages(chatId) {
  return client.get(`/session/chat/messages/${chatId}`);
}

/** Flow types from NovaFlow API */
export const FLOW_TYPE = {
  SKILL: 1,
  ASSISTANT: 5,
  WORKFLOW: 10,
};
