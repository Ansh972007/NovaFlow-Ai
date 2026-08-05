import client from "./client";
import { uploadMultipart } from "./upload";

const CHUNK_SIZE = 8 * 1024 * 1024;

export async function createConversation({ title = "New conversation", assistantId = "", conversationType = "assistant" } = {}) {
  return client.post("/conversations", {
    title,
    assistant_id: assistantId,
    conversation_type: conversationType,
  });
}

export async function uploadConversationAttachment(conversationId, file, onProgress) {
  const fileSize = file.size || 0;
  const totalChunks = Math.ceil(fileSize / CHUNK_SIZE);
  if (fileSize <= CHUNK_SIZE) {
    const formData = new FormData();
    formData.append("file", file);
    return uploadMultipart(`/conversations/${conversationId}/attachments`, formData, { onProgress });
  }

  const init = await client.post(`/conversations/${conversationId}/attachments/chunk-init`, {
    file_name: file.name,
    file_size: fileSize,
    chunk_size: CHUNK_SIZE,
    total_chunks: totalChunks,
  });
  const uploadId = init.upload_id;
  const chunkProgress = new Array(totalChunks).fill(0);
  const updateProgress = () => {
    if (!onProgress) return;
    const loaded = chunkProgress.reduce((a, b) => a + b, 0);
    onProgress({ loaded, total: fileSize, percentage: Math.min(99, Math.round((loaded / fileSize) * 100)) });
  };

  const queue = Array.from({ length: totalChunks }, (_, i) => i);
  const uploadChunk = async (idx) => {
    const start = idx * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, fileSize);
    const blob = file.slice(start, end);
    const chunkFile = new File([blob], `${file.name}.part_${idx}`);
    const formData = new FormData();
    formData.append("file", chunkFile);
    await uploadMultipart(`/conversations/${conversationId}/attachments/chunk/${uploadId}/${idx}`, formData, {
      onProgress: (pe) => {
        chunkProgress[idx] = pe.loaded || 0;
        updateProgress();
      },
    });
  };
  const workers = [];
  for (let i = 0; i < 4; i++) {
    workers.push(
      (async () => {
        while (queue.length) {
          const idx = queue.shift();
          if (idx === undefined) return;
          await uploadChunk(idx);
        }
      })()
    );
  }
  await Promise.all(workers);
  const complete = await client.post(`/conversations/${conversationId}/attachments/chunk-complete/${uploadId}`);
  onProgress?.({ loaded: fileSize, total: fileSize, percentage: 100 });
  return complete;
}
