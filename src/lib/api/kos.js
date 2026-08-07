import client from "./client";

export async function searchKnowledgeEntities({ q = "", entityType = "", limit = 50 } = {}) {
  return client.get("/kos/graph/entities", {
    params: { q, entity_type: entityType, limit },
  });
}

export async function getKnowledgeEntityGraph(entityId) {
  return client.get(`/kos/graph/entities/${entityId}`);
}

export async function buildKnowledgeGraphForFile(fileId) {
  return client.post(`/kos/documents/${fileId}/build-graph`);
}

export async function createKnowledgeSyncJob(collectionId, payload = {}) {
  return client.post(`/kos/collections/${collectionId}/sync`, payload);
}

export async function runKnowledgeSyncJob(jobId) {
  return client.post(`/kos/sync/${jobId}/run`);
}
