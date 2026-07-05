import client from "./client";

export async function listEvalSuites() {
  return client.get("/eval/suites");
}

export async function getEvalSuite(id) {
  return client.get(`/eval/suites/${id}`);
}

export async function createEvalSuite(payload) {
  return client.post("/eval/suites", payload);
}

export async function deleteEvalSuite(id) {
  return client.delete(`/eval/suites/${id}`);
}

export async function addEvalCase(suiteId, payload) {
  return client.post(`/eval/suites/${suiteId}/cases`, payload);
}

export async function deleteEvalCase(suiteId, caseId) {
  return client.delete(`/eval/suites/${suiteId}/cases/${caseId}`);
}

export async function runEvalSuite(suiteId) {
  return client.post(`/eval/suites/${suiteId}/run`);
}

export async function getEvalRun(runId) {
  return client.get(`/eval/runs/${runId}`);
}
