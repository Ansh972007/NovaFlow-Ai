"use client";

import { useRef } from "react";

export default function ChatInput({ onSend, onStop, disabled, streaming }) {
  const inputRef = useRef(null);

  function handleSubmit(e) {
    e.preventDefault();
    const value = inputRef.current?.value?.trim();
    if (!value) return;
    onSend(value);
    if (inputRef.current) {
      inputRef.current.value = "";
      inputRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function autoResize() {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }

  return (
    <div className="shrink-0 border-t border-neutral-200/80 bg-white/80 px-4 py-4 backdrop-blur-md sm:px-6">
      <form onSubmit={handleSubmit} className="mx-auto max-w-2xl">
        <div className="chat-composer flex items-end gap-2 p-2 pl-4">
          <textarea
            ref={inputRef}
            rows={1}
            disabled={disabled && !streaming}
            onKeyDown={handleKeyDown}
            onInput={autoResize}
            placeholder="Send a message…"
            className="max-h-36 min-h-[40px] flex-1 resize-none bg-transparent py-2.5 text-sm leading-relaxed text-neutral-900 outline-none placeholder:text-neutral-400 disabled:opacity-50"
          />

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              className="mb-1 shrink-0 rounded-full border border-neutral-300 px-3 py-2 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={disabled}
              className="chat-send-btn mb-1 shrink-0"
              aria-label="Send"
            >
              ↑
            </button>
          )}
        </div>
        <p className="mt-2 text-center text-[10px] text-neutral-400">
          Enter to send · Shift+Enter new line
        </p>
      </form>
    </div>
  );
}
