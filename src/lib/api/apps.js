import client from "./client";

/** Online assistants & workflows available for chat */
export async function getOnlineApps(params = {}) {
  return client.get("/chat/online", {
    params: { page: 1, limit: 50, ...params },
  });
}

/** All assistants (including offline — for empty online list) */
export async function getAssistants(params = {}) {
  return client.get("/assistant", {
    params: { page: 1, limit: 50, ...params },
  });
}

/** Assistant detail */
export async function getAssistantInfo(id) {
  return client.get(`/assistant/info/${id}`);
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
