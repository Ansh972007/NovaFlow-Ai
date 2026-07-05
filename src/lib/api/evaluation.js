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

export async function listEvalTemplates() {
  return client.get("/eval/templates");
}

export async function createSuiteFromTemplate(payload) {
  return client.post("/eval/suites/from-template", payload);
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

export async function runEvalSuite(suiteId, options = {}) {
  return client.post(`/eval/suites/${suiteId}/run`, options);
}

export async function importEvalCasesCsv(suiteId, csv) {
  return client.post(`/eval/suites/${suiteId}/import-csv`, { csv });
}

export async function compareEvalSuite(suiteId, payload) {
  return client.post(`/eval/suites/${suiteId}/compare`, payload);
}

export async function listEvalSchedules() {
  return client.get("/eval/schedules");
}

export async function createEvalSchedule(payload) {
  return client.post("/eval/schedules", payload);
}

export async function updateEvalSchedule(id, payload) {
  return client.patch(`/eval/schedules/${id}`, payload);
}

export async function deleteEvalSchedule(id) {
  return client.delete(`/eval/schedules/${id}`);
}

export async function triggerEvalSchedule(id) {
  return client.post(`/eval/schedules/${id}/trigger`);
}

export async function listEvalComparisons() {
  return client.get("/eval/comparisons");
}

export async function getSuiteTrends(suiteId, limit = 30) {
  return client.get(`/eval/suites/${suiteId}/trends`, { params: { limit } });
}

export async function getComparisonTrends(suiteId, limit = 20) {
  const params = { limit };
  if (suiteId) params.suite_id = suiteId;
  return client.get("/eval/comparisons/trends", { params });
}

export async function listEvalAlerts() {
  return client.get("/eval/alerts");
}

export async function createEvalAlert(payload) {
  return client.post("/eval/alerts", payload);
}

export async function updateEvalAlert(id, payload) {
  return client.patch(`/eval/alerts/${id}`, payload);
}

export async function deleteEvalAlert(id) {
  return client.delete(`/eval/alerts/${id}`);
}

export async function getEvalRun(runId) {
  return client.get(`/eval/runs/${runId}`);
}

export async function getEvalRunDiff(runId, baselineRunId) {
  const params = baselineRunId ? { baseline_run_id: baselineRunId } : {};
  return client.get(`/eval/runs/${runId}/diff`, { params });
}
