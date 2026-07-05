import client from "./client";

export async function listFineTuneDatasets() {
  return client.get("/finetune/datasets");
}

export async function getFineTuneDataset(id) {
  return client.get(`/finetune/datasets/${id}`);
}

export async function createFineTuneDataset(payload) {
  return client.post("/finetune/datasets", payload);
}

export async function updateFineTuneDataset(id, payload) {
  return client.patch(`/finetune/datasets/${id}`, payload);
}

export async function deleteFineTuneDataset(id) {
  return client.delete(`/finetune/datasets/${id}`);
}

export async function listFineTuneJobs() {
  return client.get("/finetune/jobs");
}

export async function startFineTuneJob(payload) {
  return client.post("/finetune/jobs", payload);
}

export async function refreshFineTuneJob(id) {
  return client.post(`/finetune/jobs/${id}/refresh`);
}
