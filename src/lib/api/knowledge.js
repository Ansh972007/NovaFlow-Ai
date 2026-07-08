import client from "./client";
import { uploadMultipart } from "./upload";

export const FILE_STATUS = {
  1: { label: "Processing", color: "text-amber-700 bg-amber-50 border-amber-200" },
  2: { label: "Ready", color: "text-green-700 bg-green-50 border-green-200" },
  3: { label: "Failed", color: "text-red-700 bg-red-50 border-red-200" },
  4: { label: "Rebuilding", color: "text-amber-700 bg-amber-50 border-amber-200" },
  5: { label: "Queued", color: "text-neutral-600 bg-neutral-50 border-border" },
  6: { label: "Timeout", color: "text-red-700 bg-red-50 border-red-200" },
};

export async function listKnowledge({ page = 1, pageSize = 50, name = "", type = 0 } = {}) {
  return client.get("/knowledge", {
    params: { page_num: page, page_size: pageSize, name, type },
  });
}

export async function getEmbeddingModels() {
  return client.get("/knowledge/embedding_param");
}

export async function createKnowledge({ name, description = "", model, type = 0 }) {
  return client.post("/knowledge/create", {
    name,
    description,
    model,
    type,
  });
}

export async function getKnowledgeFiles(knowledgeId, { page = 1, pageSize = 50 } = {}) {
  return client.get(`/knowledge/file_list/${knowledgeId}`, {
    params: { page_num: page, page_size: pageSize },
  });
}

export async function uploadKnowledgeFile(knowledgeId, file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  return uploadMultipart(`/knowledge/upload/${knowledgeId}`, formData, { onProgress });
}

export async function processKnowledgeFiles(knowledgeId, filePaths) {
  return client.post("/knowledge/process", {
    knowledge_id: knowledgeId,
    separator: ["\n\n", "\n"],
    separator_rule: ["after", "after"],
    chunk_size: 1000,
    chunk_overlap: 100,
    file_list: filePaths.map((file_path) => ({ file_path })),
  });
}

export async function retryKnowledgeFile(data) {
  return client.post("/knowledge/retry", data);
}

export async function ingestKnowledgeUrl(knowledgeId, url) {
  return client.post(`/knowledge/ingest-url/${knowledgeId}`, { url });
}

/** Search indexed chunks (Q&A preview) */
export async function searchKnowledgeChunks(knowledgeId, keyword, { page = 1, limit = 6 } = {}) {
  if (!keyword?.trim()) return { data: [], total: 0, method: "none" };
  // Prefer semantic search (vector + keyword fallback)
  try {
    return await client.get("/knowledge/search", {
      params: {
        knowledge_id: knowledgeId,
        q: keyword.trim(),
        limit,
      },
    });
  } catch {
    return client.get("/knowledge/chunk", {
      params: {
        knowledge_id: knowledgeId,
        keyword: keyword.trim(),
        page,
        limit,
      },
    });
  }
}
