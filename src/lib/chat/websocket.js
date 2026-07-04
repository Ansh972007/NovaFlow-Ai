import { FLOW_TYPE } from "@/lib/api/apps";

function getWsUrl(path) {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";
  const url = new URL(apiUrl);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("nf_token")
      : null;
  const tokenQuery = token ? `?t=${encodeURIComponent(token)}` : "";
  return `${protocol}//${url.host}${path}${tokenQuery}`;
}

function buildInitPayload(app, chatId) {
  return {
    chatHistory: [],
    chat_id: chatId,
    flow_id: app.id,
    inputs: {
      data: {
        id: app.id,
        chatId,
        type: app.flow_type ?? FLOW_TYPE.ASSISTANT,
      },
    },
    name: app.name,
    description: app.description || app.desc || "",
  };
}

function buildSendPayload(app, chatId, message) {
  const flowType = app.flow_type ?? FLOW_TYPE.ASSISTANT;
  if (flowType === FLOW_TYPE.ASSISTANT) {
    return {
      chatHistory: [],
      flow_id: app.id,
      chat_id: chatId,
      name: app.name,
      description: app.description || app.desc || "",
      inputs: {
        data: { chatId, id: app.id, type: FLOW_TYPE.ASSISTANT },
        input: message,
      },
    };
  }
  return {
    action: "input",
    chat_id: chatId,
    flow_id: app.id,
    data: {
      dialog_input: {
        data: { user_input: message },
        message,
        category: "question",
      },
    },
  };
}

function parseError(data) {
  try {
    if (typeof data.message === "string") {
      const parsed = JSON.parse(data.message);
      return parsed.status_message || data.message;
    }
    return data.message?.status_message || "Something went wrong";
  } catch {
    return "Something went wrong";
  }
}

export class AssistantChatSocket {
  constructor({ app, chatId, handlers }) {
    this.app = app;
    this.chatId = chatId;
    this.handlers = handlers;
    this.ws = null;
    this.connected = false;
  }

  getWsPath() {
    const flowType = this.app.flow_type ?? FLOW_TYPE.ASSISTANT;
    if (flowType === FLOW_TYPE.WORKFLOW) {
      return `/api/v1/workflow/chat/${this.app.id}?chat_id=${this.chatId}`;
    }
    if (flowType === FLOW_TYPE.ASSISTANT) {
      return `/api/v1/assistant/chat/${this.app.id}`;
    }
    return `/api/v1/chat/${this.app.id}?type=L1`;
  }

  connect() {
    return new Promise((resolve, reject) => {
      const url = getWsUrl(this.getWsPath());
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.connected = true;
        const flowType = this.app.flow_type ?? FLOW_TYPE.ASSISTANT;
        if (flowType === FLOW_TYPE.WORKFLOW) {
          this.ws.send(
            JSON.stringify({
              action: "init_data",
              chat_id: this.chatId,
              flow_id: this.app.id,
              data: this.app,
            })
          );
        } else {
          this.ws.send(JSON.stringify(buildInitPayload(this.app, this.chatId)));
        }
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (err) {
          this.handlers.onError?.(err.message);
        }
      };

      this.ws.onerror = () => {
        this.handlers.onError?.("WebSocket connection failed");
        reject(new Error("WebSocket connection failed"));
      };

      this.ws.onclose = () => {
        this.connected = false;
        this.handlers.onDisconnect?.();
      };
    });
  }

  handleMessage(data) {
    if (data.category === "error" || data.type === "error") {
      this.handlers.onError?.(parseError(data));
      this.handlers.onDone?.();
      return;
    }

    if (data.category === "guide_word") {
      const text = data.message?.guide_word || data.message?.msg || "";
      if (text) this.handlers.onGuide?.(text);
      return;
    }

    if (data.category === "stream_msg") {
      const chunk = data.message?.msg ?? "";
      if (data.type === "end") {
        this.handlers.onStreamEnd?.(chunk, data);
      } else {
        this.handlers.onStream?.(chunk, data);
      }
      return;
    }

    if (data.type === "start") {
      this.handlers.onStart?.(data);
    } else if (data.type === "stream") {
      const chunk =
        typeof data.message === "object"
          ? data.message?.content || ""
          : data.message || "";
      const reasoning = data.message?.reasoning_content || "";
      this.handlers.onStream?.(chunk, data, reasoning);
    } else if (data.type === "end" || data.type === "end_cover") {
      this.handlers.onStreamEnd?.(
        typeof data.message === "string" ? data.message : data.message?.content || "",
        data
      );
    } else if (data.type === "close") {
      this.handlers.onDone?.();
    }
  }

  sendMessage(text) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("Not connected");
    }
    this.ws.send(JSON.stringify(buildSendPayload(this.app, this.chatId, text)));
  }

  stop() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "stop" }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }
}
