/**
 * Chat voice input — browser SpeechRecognition first, NovaFlow /voice/stream fallback.
 */

import { getWsUrl } from "@/lib/api/config";

const NAV_ALIASES = {
  workflows: "/workflows",
  workflow: "/workflows",
  credentials: "/credentials",
  credential: "/credentials",
  vault: "/credentials",
  chat: "/chat",
  projects: "/projects",
  project: "/projects",
  marketplace: "/marketplace",
  developer: "/developer",
  agents: "/developer",
  schedules: "/workflows?tab=schedules",
};

/**
 * Classify a final transcript as a voice command or plain dictation.
 * @returns {{ action: string, phrase?: string, path?: string } | null}
 */
export function classifyVoiceCommand(text) {
  const cleaned = String(text || "").trim().toLowerCase();
  if (!cleaned) return null;

  if (/^(please\s+)?(approve|yes|confirm)(\s+it|\s+the\s+plan)?$/.test(cleaned)) {
    return { action: "suggest", phrase: "approve" };
  }
  if (/^(please\s+)?(deploy|ship)(\s+it|\s+this)?$/.test(cleaned)) {
    return { action: "suggest", phrase: "deploy" };
  }
  if (/^(please\s+)?(continue|proceed)$/.test(cleaned)) {
    return { action: "suggest", phrase: "continue" };
  }
  if (/^(please\s+)?(cancel|reject)(\s+it)?$/.test(cleaned)) {
    return { action: "suggest", phrase: "cancel" };
  }
  if (/^(run\s+)?(my\s+)?(last\s+)?workflow$|^run\s+workflow$/.test(cleaned)) {
    return { action: "suggest", phrase: "Run my last workflow" };
  }
  if (/^heal(\s+again)?$/.test(cleaned)) {
    return { action: "suggest", phrase: cleaned.includes("again") ? "heal again" : "heal" };
  }
  if (/^what can you do\??$|^capabilities$|^help$/.test(cleaned)) {
    return { action: "suggest", phrase: "What can you do?" };
  }
  if (/^workspace health$|^health report$/.test(cleaned)) {
    return { action: "suggest", phrase: "Workspace health" };
  }
  if (/^list schedules$|^show schedules$/.test(cleaned)) {
    return { action: "suggest", phrase: "List schedules" };
  }
  if (/^export (this )?(chat|conversation)( as markdown)?$/.test(cleaned)) {
    return { action: "suggest", phrase: "Export this chat as markdown" };
  }
  if (/^finops( summary)?$|^show (ai )?costs$/.test(cleaned)) {
    return { action: "suggest", phrase: "FinOps summary" };
  }
  if (/^enterprise playbooks?$|^list playbooks$/.test(cleaned)) {
    return { action: "suggest", phrase: "Enterprise playbooks" };
  }

  const runWf = cleaned.match(/\b(?:run|execute)\s+workflow\s+(.+)$/);
  if (runWf) {
    return { action: "suggest", phrase: `Run workflow ${runWf[1].trim()}` };
  }

  const nav = cleaned.match(/\b(?:go\s+to|navigate\s+to|open|show)\s+([a-z0-9_\-\s]+)$/);
  if (nav) {
    const target = nav[1].trim();
    const key = target.replace(/\s+/g, "_").replace(/-/g, "_");
    const first = key.split("_")[0];
    const path = NAV_ALIASES[key] || NAV_ALIASES[first] || NAV_ALIASES[target];
    if (path) return { action: "navigate", path, phrase: target };
  }

  return null;
}

export function getSpeechRecognitionCtor() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function speechRecognitionSupported() {
  return Boolean(getSpeechRecognitionCtor());
}

/**
 * Start continuous dictation into callbacks.
 * Returns a controller with stop().
 */
export function startBrowserDictation({
  onPartial,
  onFinal,
  onError,
  lang = "en-US",
} = {}) {
  const Ctor = getSpeechRecognitionCtor();
  if (!Ctor) {
    onError?.(new Error("Speech recognition is not supported in this browser."));
    return null;
  }

  const recognition = new Ctor();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = lang;

  recognition.onresult = (event) => {
    let interim = "";
    let finalChunk = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      const text = result?.[0]?.transcript || "";
      if (result.isFinal) finalChunk += text;
      else interim += text;
    }
    if (interim) onPartial?.(interim);
    if (finalChunk) onFinal?.(finalChunk);
  };

  recognition.onerror = (event) => {
    const msg = event?.error || "speech_error";
    if (msg === "aborted" || msg === "no-speech") return;
    onError?.(new Error(String(msg)));
  };

  recognition.start();

  return {
    mode: "browser",
    stop() {
      try {
        recognition.stop();
      } catch {
        /* ignore */
      }
      try {
        recognition.abort();
      } catch {
        /* ignore */
      }
    },
  };
}

/**
 * Record microphone audio and send to NovaFlow voice WS for transcript.
 * Returns a controller with stop() that resolves when transcript arrives (or timeout).
 */
export function startServerVoiceCapture({ onTranscript, onError, onStatus } = {}) {
  if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    onError?.(new Error("Microphone is not available in this browser."));
    return null;
  }

  let mediaStream = null;
  let recorder = null;
  let ws = null;
  let stopped = false;
  const chunks = [];

  const cleanup = () => {
    try {
      ws?.close();
    } catch {
      /* ignore */
    }
    ws = null;
    try {
      mediaStream?.getTracks?.().forEach((t) => t.stop());
    } catch {
      /* ignore */
    }
    mediaStream = null;
    recorder = null;
  };

  const run = async () => {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      recorder = mime ? new MediaRecorder(mediaStream, { mimeType: mime }) : new MediaRecorder(mediaStream);

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      ws = new WebSocket(getWsUrl("/api/v1/voice/stream"));
      ws.binaryType = "arraybuffer";

      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("Voice session timeout")), 10000);
        ws.onopen = () => {};
        ws.onerror = () => {
          clearTimeout(timer);
          reject(new Error("Voice WebSocket failed"));
        };
        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data);
            if (data.type === "session_ready") {
              clearTimeout(timer);
              resolve();
            } else if (data.type === "error") {
              clearTimeout(timer);
              reject(new Error(data.message || "Voice error"));
            }
          } catch {
            /* ignore non-json */
          }
        };
      });

      onStatus?.("listening");
      recorder.start(250);

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "transcript" && data.text) {
            onTranscript?.(String(data.text));
          } else if (data.type === "error") {
            onError?.(new Error(data.message || "Voice error"));
          }
        } catch {
          /* ignore */
        }
      };
    } catch (err) {
      cleanup();
      onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  };

  run();

  return {
    mode: "server",
    async stop() {
      if (stopped) return;
      stopped = true;
      onStatus?.("processing");
      try {
        if (recorder && recorder.state !== "inactive") {
          await new Promise((resolve) => {
            recorder.onstop = resolve;
            try {
              recorder.stop();
            } catch {
              resolve();
            }
          });
        }
        const blob = new Blob(chunks, { type: recorder?.mimeType || "audio/webm" });
        if (ws && ws.readyState === WebSocket.OPEN && blob.size > 0) {
          const buf = await blob.arrayBuffer();
          ws.send(buf);
          // Give server a moment to reply with transcript
          await new Promise((r) => setTimeout(r, 1500));
          try {
            ws.send(JSON.stringify({ action: "stop" }));
          } catch {
            /* ignore */
          }
        }
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error(String(err)));
      } finally {
        cleanup();
        onStatus?.("idle");
      }
    },
  };
}

/**
 * Start the best available voice input path.
 */
export function startVoiceInput(handlers = {}) {
  if (speechRecognitionSupported()) {
    return startBrowserDictation(handlers);
  }
  return startServerVoiceCapture({
    onTranscript: (text) => handlers.onFinal?.(text),
    onError: handlers.onError,
    onStatus: handlers.onStatus,
  });
}
