import { FLOW_TYPE } from "@/lib/api/apps";
import { getWsUrl } from "@/lib/api/config";

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

function buildSendPayload(app, chatId, message, history = [], options = {}) {
  const prior = (history || [])
    .filter((m) => m && (m.role === "user" || m.role === "assistant") && m.content)
    .map((m) => ({ role: m.role, content: String(m.content).slice(0, 4000) }))
    .slice(-12);

  const flowType = app.flow_type ?? FLOW_TYPE.ASSISTANT;
  if (flowType === FLOW_TYPE.ASSISTANT) {
    return {
      chatHistory: prior,
      flow_id: app.id,
      chat_id: chatId,
      conversation_id: options.conversationId || "",
      attachment_ids: options.attachmentIds || [],
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
    chatHistory: prior,
    conversation_id: options.conversationId || "",
    attachment_ids: options.attachmentIds || [],
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
      const raw = data.message.trim();
      // Structured API errors are JSON; friendly LLM errors are plain text
      if (raw.startsWith("{") || raw.startsWith("[")) {
        try {
          const parsed = JSON.parse(raw);
          return parsed.status_message || parsed.message || raw;
        } catch {
          return raw || "Something went wrong";
        }
      }
      return raw || "Something went wrong";
    }
    if (data.message && typeof data.message === "object") {
      return data.message.status_message || data.message.message || "Something went wrong";
    }
    return "Something went wrong";
  } catch {
    return typeof data?.message === "string" ? data.message : "Something went wrong";
  }
}

export class AssistantChatSocket {
  constructor({ app, chatId, handlers }) {
    this.app = app;
    this.chatId = chatId;
    this.handlers = handlers;
    this.ws = null;
    this.connected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.heartbeatInterval = null;
    this.heartbeatMissed = 0;
    this.lastHeartbeatResponse = Date.now();
    this.connectionHealthCheck = null;
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

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: "ping" }));
          this.heartbeatMissed++;
          
          // If we miss 3 consecutive heartbeats, consider connection dead
          if (this.heartbeatMissed > 3) {
            console.warn("WebSocket heartbeat missed, reconnecting...");
            this.ws.close();
          }
        } catch (error) {
          console.error("Heartbeat send failed:", error);
          this.ws.close();
        }
      }
    }, 30000); // 30 second heartbeat
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    this.heartbeatMissed = 0;
  }

  startConnectionHealthCheck() {
    this.stopConnectionHealthCheck();
    this.connectionHealthCheck = setInterval(() => {
      const timeSinceLastResponse = Date.now() - this.lastHeartbeatResponse;
      
      // If no response for 2 minutes, connection might be stale
      if (timeSinceLastResponse > 120000 && this.connected) {
        console.warn("WebSocket connection appears stale, reconnecting...");
        if (this.ws) {
          this.ws.close();
        }
      }
    }, 60000); // Check every minute
  }

  stopConnectionHealthCheck() {
    if (this.connectionHealthCheck) {
      clearInterval(this.connectionHealthCheck);
      this.connectionHealthCheck = null;
    }
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        const url = getWsUrl(this.getWsPath());
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          this.connected = true;
          this.reconnectAttempts = 0;
          this.lastHeartbeatResponse = Date.now();
          this.heartbeatMissed = 0;
          
          // Start heartbeat and health monitoring
          this.startHeartbeat();
          this.startConnectionHealthCheck();
          
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
            
            // Reset heartbeat counter on any message
            this.heartbeatMissed = 0;
            this.lastHeartbeatResponse = Date.now();
            
            // Handle pong response
            if (data.type === "pong") {
              return;
            }
            
            this.handleMessage(data);
          } catch (err) {
            this.handlers.onError?.(err.message);
          }
        };

        this.ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          this.handlers.onError?.("WebSocket connection failed");
          
          // Stop health monitoring
          this.stopHeartbeat();
          this.stopConnectionHealthCheck();
          
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
              this.connect().catch(() => {
                reject(new Error("WebSocket connection failed"));
              });
            }, delay);
          } else {
            reject(new Error("WebSocket connection failed"));
          }
        };

        this.ws.onclose = (event) => {
          this.connected = false;
          
          // Stop health monitoring
          this.stopHeartbeat();
          this.stopConnectionHealthCheck();
          
          if (event.code !== 1000) {
            console.warn("WebSocket closed unexpectedly:", event.code, event.reason);
            // Attempt reconnection for abnormal closures
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
              this.reconnectAttempts++;
              const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
              console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
              
              setTimeout(() => {
                this.connect().catch(() => {
                  this.handlers.onDisconnect?.();
                });
              }, delay);
            } else {
              this.handlers.onDisconnect?.();
            }
          } else {
            this.handlers.onDisconnect?.();
          }
        };
      } catch (error) {
        console.error("WebSocket connection error:", error);
        reject(error);
      }
    });
  }

  handleMessage(data) {
    if (data.type === "conversation") {
      this.handlers.onConversation?.(data.conversation_id);
      return;
    }
    if (String(data.type || "").startsWith("aios_")) {
      this.handlers.onAiosEvent?.(data);
      return;
    }
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

  async sendMessage(text, history = [], options = {}) {
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED || this.ws.readyState === WebSocket.CLOSING) {
      await this.connect();
    }
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      await new Promise((resolve) => {
        const check = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            clearInterval(check);
            resolve();
          }
        }, 50);
        setTimeout(() => {
          clearInterval(check);
          resolve();
        }, 4000);
      });
    }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(buildSendPayload(this.app, this.chatId, text, history, options)));
    } else {
      throw new Error("Could not connect to NovaFlow API backend on port 3001. Please make sure Docker containers are online.");
    }
  }

  stop() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "stop" }));
    }
  }

  disconnect() {
    this.stopHeartbeat();
    this.stopConnectionHealthCheck();
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
    this.reconnectAttempts = 0;
  }
}
