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

export async function importFineTuneCsv(datasetId, csv) {
  return client.post(`/finetune/datasets/${datasetId}/import-csv`, { csv });
}

export async function applyFineTuneJob(jobId, options = {}) {
  return client.post(`/finetune/jobs/${jobId}/apply`, options);
}

export async function estimateFineTuneCost(datasetId, baseModel = "gpt-4o-mini-2024-07-18") {
  return client.get(`/finetune/datasets/${datasetId}/estimate`, {
    params: { base_model: baseModel },
  });
}

export async function listAbRoutes() {
  return client.get("/finetune/ab-routes");
}

export async function createAbRoute(payload) {
  return client.post("/finetune/ab-routes", payload);
}

export async function deleteAbRoute(id) {
  return client.delete(`/finetune/ab-routes/${id}`);
}
