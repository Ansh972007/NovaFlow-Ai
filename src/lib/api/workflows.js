import client from "./client";
import { getApiBaseUrl } from "./config";

function getWsUrl(path) {
  const apiUrl = getApiBaseUrl();
  const url = new URL(apiUrl);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const token =
    typeof window !== "undefined" ? localStorage.getItem("nf_token") : null;
  const tokenQuery = token ? `?t=${encodeURIComponent(token)}` : "";
  return `${protocol}//${url.host}${path}${tokenQuery}`;
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
  return client.get("/workflow/templates");
}

export async function getWorkflowInfo(id) {
  return client.get(`/workflow/info/${id}`);
}

export async function createWorkflow({ name, desc = "", templateId = "rag" }) {
  return client.post("/workflow", {
    name,
    desc,
    template_id: templateId,
  });
}

export async function updateWorkflow({ id, name, desc, graph }) {
  return client.put("/workflow", { id, name, desc, graph });
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

export async function getOnlineWorkflows() {
  return client.get("/workflow/online");
}
