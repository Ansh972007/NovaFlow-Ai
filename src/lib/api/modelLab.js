import client from "./client";

export async function getPromptDrift(params = {}) {
  return client.get("/model-lab/drift", { params });
}

export async function createDatasetFromKnowledge(payload) {
  return client.post("/model-lab/dataset-from-knowledge", payload);
}

export async function trainAndEval(payload) {
  return client.post("/model-lab/train-and-eval", payload);
}

export async function listPipelines() {
  return client.get("/model-lab/pipelines");
}

export async function refreshPipelineJob(jobId) {
  return client.post(`/model-lab/jobs/${jobId}/refresh`);
}

export async function deployPipelineAssistant(jobId, payload = {}) {
  return client.post(`/model-lab/jobs/${jobId}/deploy-assistant`, payload);
}
