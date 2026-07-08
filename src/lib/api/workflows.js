import client from "./client";
import { mergeWorkflowTemplates, WORKFLOW_TEMPLATES } from "@/lib/workflow/templates";
import { getApiBaseUrl, getWsQueryString } from "./config";

function getWsUrl(path) {
  const apiUrl = getApiBaseUrl();
  const url = new URL(apiUrl);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}${path}${getWsQueryString()}`;
}

export const FLOW_TYPE_WORKFLOW = 10;

export async function getWorkflowsPage(params = {}) {
  const res = await client.get("/workflow", {
    params: { page: 1, limit: 50, ...params },
  });
  if (Array.isArray(res)) return { data: res, total: res.length };
  return { data: res?.data || [], total: res?.total || 0 };
}

export async function getWorkflowTemplates() {
  try {
    const data = await client.get("/workflow/templates");
    return mergeWorkflowTemplates(Array.isArray(data) ? data : []);
  } catch {
    return WORKFLOW_TEMPLATES;
  }
}

export async function getWorkflowInfo(id, { retries = 2 } = {}) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await client.get(`/workflow/info/${id}`);
    } catch (err) {
      lastError = err;
      if (attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, 600 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

export async function createWorkflow({ name, desc = "", templateId = "rag" }) {
  return client.post("/workflow", {
    name,
    desc,
    template_id: templateId,
  });
}

export async function updateWorkflow({ id, name, desc, graph, run_webhook_url }) {
  const body = { id, name, desc, graph };
  if (run_webhook_url !== undefined) body.run_webhook_url = run_webhook_url;
  return client.put("/workflow", body);
}

export async function setWorkflowStatus(id, status) {
  return client.post("/workflow/status", { id, status });
}

export async function deleteWorkflow(workflowId) {
  return client.post("/workflow/delete", { workflow_id: workflowId });
}

export async function runWorkflow(workflowId, input) {
  return client.post("/workflow/run", { workflow_id: workflowId, input });
}

export async function resumeWorkflow(pendingRunId, { approved = true, note = "" } = {}) {
  return client.post("/workflow/resume", {
    pending_run_id: pendingRunId,
    approved,
    note,
  });
}

export function runWorkflowWs(workflowId, input, handlers = {}) {
  return new Promise((resolve, reject) => {
    const url = getWsUrl(`/api/v1/workflow/run/ws/${workflowId}`);
    const ws = new WebSocket(url);
    let result = null;

    ws.onopen = () => {
      ws.send(JSON.stringify({ input }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "error") {
          handlers.onError?.(data.message || "Run failed");
          reject(new Error(data.message || "Run failed"));
          ws.close();
          return;
        }
        if (data.type === "step") {
          handlers.onStep?.(data);
        } else if (data.type === "stream") {
          const token = data.message?.content || "";
          handlers.onStream?.(token, data);
        } else if (data.type === "human_review") {
          handlers.onHumanReview?.(data);
        } else if (data.type === "complete") {
          result = data;
          handlers.onComplete?.(data);
        } else if (data.type === "close") {
          ws.close();
          resolve(result);
        }
      } catch (err) {
        handlers.onError?.(err.message);
        reject(err);
        ws.close();
      }
    };

    ws.onerror = () => {
      const msg = "WebSocket connection failed";
      handlers.onError?.(msg);
      reject(new Error(msg));
    };

    ws.onclose = () => {
      if (result) resolve(result);
    };
  });
}

export async function getWorkflowVersions(workflowId) {
  return client.get(`/workflow/${workflowId}/versions`);
}

export async function restoreWorkflowVersion(workflowId, versionId) {
  return client.post(`/workflow/${workflowId}/versions/${versionId}/restore`);
}

export async function getWorkflowSchedules(workflowId) {
  return client.get(`/workflow/${workflowId}/schedules`);
}

export async function listWorkspaceSchedules() {
  return client.get("/workflow/schedules");
}

export async function triggerWorkflowSchedule(scheduleId) {
  return client.post(`/workflow/schedules/${scheduleId}/trigger`);
}

export async function createWorkflowSchedule(workflowId, payload) {
  return client.post(`/workflow/${workflowId}/schedules`, payload);
}

export async function updateWorkflowSchedule(scheduleId, payload) {
  return client.patch(`/workflow/schedules/${scheduleId}`, payload);
}

export async function getWorkflowVersionDiff(workflowId, fromId, toId = "current") {
  return client.get(`/workflow/${workflowId}/versions/diff`, {
    params: { from_id: fromId, to_id: toId },
  });
}

export async function touchWorkflowPresence(workflowId, payload = {}) {
  return client.post(`/workflow/${workflowId}/presence`, payload);
}

export async function getWorkflowPresence(workflowId) {
  return client.get(`/workflow/${workflowId}/presence`);
}

export async function deleteWorkflowSchedule(scheduleId) {
  return client.delete(`/workflow/schedules/${scheduleId}`);
}

export async function getWorkflowRun(runId) {
  return client.get(`/workflow/runs/${runId}`);
}

export async function listWorkspaceRuns(params = {}) {
  return client.get("/workflow/runs", { params });
}

export async function getOnlineWorkflows() {
  return client.get("/workflow/online");
}
