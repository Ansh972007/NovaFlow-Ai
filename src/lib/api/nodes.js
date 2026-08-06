import client from "./client";

export function listNodeLibrary(params = {}) {
  return client.get("/nodes/library", { params }).then((r) => r.data?.data ?? r.data);
}

export function getNodeDefinition(id) {
  return client.get(`/nodes/library/${id}`).then((r) => r.data?.data ?? r.data);
}

export function createNodeDefinition(body) {
  return client.post("/nodes/library", body).then((r) => r.data?.data ?? r.data);
}

export function updateNodeDefinition(id, body) {
  return client.patch(`/nodes/library/${id}`, body).then((r) => r.data?.data ?? r.data);
}

export function probeNodeHttp(body) {
  return client.post("/nodes/library/probe", body).then((r) => r.data?.data ?? r.data);
}

export function testNodeDefinition(id, body = {}) {
  return client.post(`/nodes/library/${id}/test`, body).then((r) => r.data?.data ?? r.data);
}

export function publishNodeDefinition(id, body = {}) {
  return client.post(`/nodes/library/${id}/publish`, body).then((r) => r.data?.data ?? r.data);
}

export function deprecateNodeDefinition(id) {
  return client.post(`/nodes/library/${id}/deprecate`).then((r) => r.data?.data ?? r.data);
}
