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

export const KB_STATUS_LABELS = {
  ready: { label: "Ready", color: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60" },
  indexing: { label: "Indexing", color: "bg-amber-50 text-amber-800 ring-1 ring-amber-200/60" },
  empty: { label: "Empty", color: "bg-neutral-100 text-neutral-500 ring-1 ring-neutral-200/60" },
};

export async function listKnowledge({ page = 1, pageSize = 50, name = "", type = 0 } = {}) {
  return client.get("/knowledge", {
    params: { page_num: page, page_size: pageSize, name, type },
  });
}

export async function getKnowledgeById(knowledgeId) {
  return client.get(`/knowledge/${knowledgeId}`);
}

export async function getEmbeddingModels() {
  return client.get("/knowledge/embedding_param");
}

export async function createKnowledge({ name, description = "", model, type = 0, classification = "internal" }) {
  return client.post("/knowledge/create", {
    name,
    description,
    model,
    type,
    classification,
  });
}

export async function getKnowledgeFiles(knowledgeId, { page = 1, pageSize = 50 } = {}) {
  return client.get(`/knowledge/file_list/${knowledgeId}`, {
    params: { page_num: page, page_size: pageSize },
  });
}

export async function deleteKnowledgeFile(fileId) {
  return client.delete(`/knowledge/file/${fileId}`);
}

export async function uploadKnowledgeFile(knowledgeId, file, onProgress) {
  const CHUNK_SIZE = 8 * 1024 * 1024; // 8MB chunks
  const fileSize = file.size;
  const totalChunks = Math.ceil(fileSize / CHUNK_SIZE);

  if (fileSize <= CHUNK_SIZE) {
    const formData = new FormData();
    formData.append("file", file);
    return uploadMultipart(`/knowledge/upload/${knowledgeId}`, formData, { onProgress });
  }

  const initRes = await client.post(`/knowledge/upload-chunk/init/${knowledgeId}`, {
    file_name: file.name,
    file_size: fileSize,
    chunk_size: CHUNK_SIZE,
    total_chunks: totalChunks,
  });

  const uploadId = initRes.upload_id;
  const uploadedChunks = initRes.uploaded_chunks || [];

  const chunkProgress = new Array(totalChunks).fill(0);
  const updateOverallProgress = () => {
    if (!onProgress) return;
    const totalUploaded = chunkProgress.reduce((a, b) => a + b, 0);
    const pct = Math.min(99, Math.round((totalUploaded / fileSize) * 100));
    onProgress({ loaded: totalUploaded, total: fileSize, percentage: pct });
  };

  const CONCURRENCY = 4;
  const queue = [];
  for (let idx = 0; idx < totalChunks; idx++) {
    if (uploadedChunks.includes(idx)) {
      chunkProgress[idx] = Math.min(fileSize - idx * CHUNK_SIZE, CHUNK_SIZE);
      continue;
    }
    queue.push(idx);
  }

  const uploadChunkTask = async (chunkIndex) => {
    const start = chunkIndex * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, fileSize);
    const chunkBlob = file.slice(start, end);
    const chunkFile = new File([chunkBlob], `${file.name}.part_${chunkIndex}`);

    const formData = new FormData();
    formData.append("file", chunkFile);

    await uploadMultipart(`/knowledge/upload-chunk/${uploadId}/${chunkIndex}`, formData, {
      onProgress: (pe) => {
        chunkProgress[chunkIndex] = pe.loaded || 0;
        updateOverallProgress();
      },
    });
  };

  const workers = [];
  for (let i = 0; i < CONCURRENCY; i++) {
    workers.push(
      (async () => {
        while (queue.length > 0) {
          const chunkIndex = queue.shift();
          if (chunkIndex === undefined) break;

          let attempts = 3;
          while (attempts > 0) {
            try {
              await uploadChunkTask(chunkIndex);
              break;
            } catch (err) {
              attempts--;
              if (attempts === 0) throw err;
              await new Promise((resolve) => setTimeout(resolve, 1500));
            }
          }
        }
      })()
    );
  }

  await Promise.all(workers);

  const completeRes = await client.post(`/knowledge/upload-chunk/complete/${uploadId}`);
  if (onProgress) {
    onProgress({ loaded: fileSize, total: fileSize, percentage: 100 });
  }
  return completeRes;
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

/** Search indexed chunks (keyword browse) */
export async function searchKnowledgeChunks(knowledgeId, keyword, { page = 1, limit = 6 } = {}) {
  if (!keyword?.trim()) return { data: [], total: 0, method: "none" };
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

/** Extractive retrieve — no LLM required */
export async function retrieveKnowledge(knowledgeId, question, { limit = 5 } = {}) {
  if (!question?.trim()) {
    return {
      extractive_digest: "",
      data: [],
      total: 0,
      method: "none",
      citations: [],
      embedding_available: false,
      llm_answer_available: false,
    };
  }
  return client.post("/knowledge/retrieve", {
    knowledge_id: knowledgeId,
    q: question.trim(),
    limit,
  });
}

/** Grounded answer over one knowledge base (falls back to extractive when no LLM) */
export async function answerKnowledgeQuestion(knowledgeId, question, { limit = 5 } = {}) {
  if (!question?.trim()) {
    return { answer: "", data: [], total: 0, method: "none", citations: [] };
  }
  return client.post("/knowledge/answer", {
    knowledge_id: knowledgeId,
    q: question.trim(),
    limit,
  });
}
