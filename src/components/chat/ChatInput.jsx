"use client";

import { useRef } from "react";

export default function ChatInput({ onSend, onStop, disabled, streaming }) {
  const inputRef = useRef(null);

  function handleSubmit(e) {
    e.preventDefault();
    const value = inputRef.current?.value?.trim();
    if (!value) return;
    onSend(value);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border bg-white/80 p-4 backdrop-blur-xl">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          ref={inputRef}
          rows={1}
          disabled={disabled && !streaming}
          onKeyDown={handleKeyDown}
          placeholder="Message NovaFlow AI…"
          className="input-field max-h-32 min-h-[48px] flex-1 resize-none py-3 disabled:opacity-50"
        />
        {streaming ? (
          <button
            type="button"
            onClick={onStop}
            className="btn-secondary !rounded-xl !px-4"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={disabled}
            className="btn-primary !rounded-xl !px-5 disabled:opacity-50"
          >
            Send
          </button>
        )}
      </div>
    </form>
  );
}
