import client from "./client";

export async function listAgentTools() {
  return client.get("/agents/tools");
}

export async function runAgent(payload) {
  return client.post("/agents/run", payload);
}
