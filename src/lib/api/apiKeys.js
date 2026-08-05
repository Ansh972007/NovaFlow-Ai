import client from "./client";

export async function listApiKeys() {
  return client.get("/api-keys");
}

export async function createApiKey(payload) {
  const name = typeof payload === "string" ? payload : payload?.name;
  return client.post("/api-keys", { name: name || "API key" });
}

export async function deleteApiKey(payload) {
  const id = typeof payload === "object" ? payload?.id : payload;
  return client.post("/api-keys/delete", { id });
}
