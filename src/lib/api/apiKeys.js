import client from "./client";

export async function listApiKeys() {
  return client.get("/api-keys");
}

export async function createApiKey(name) {
  return client.post("/api-keys", { name });
}

export async function deleteApiKey(id) {
  return client.post("/api-keys/delete", { id });
}
