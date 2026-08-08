import client from "./client";

export function listNodeLibrary(params = {}) {
  return client.get("/nodes/library", { params });
}

export function getNodeDefinition(id) {
  return client.get(`/nodes/library/${id}`);
}

export function createNodeDefinition(body) {
  return client.post("/nodes/library", body);
}

export function updateNodeDefinition(id, body) {
  return client.patch(`/nodes/library/${id}`, body);
}

export function probeNodeHttp(body) {
  return client.post("/nodes/library/probe", body);
}

export function testNodeDefinition(id, body = {}) {
  return client.post(`/nodes/library/${id}/test`, body);
}

export function publishNodeDefinition(id, body = {}) {
  return client.post(`/nodes/library/${id}/publish`, body);
}

export function deprecateNodeDefinition(id) {
  return client.post(`/nodes/library/${id}/deprecate`);
}
