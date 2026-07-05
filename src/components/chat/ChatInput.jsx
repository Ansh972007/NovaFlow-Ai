"use client";

import { motion } from "framer-motion";
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
    <div className="shrink-0 border-t border-neutral-200/40 bg-white/45 px-4 py-5 backdrop-blur-lg sm:px-6">
      <motion.form
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
        onSubmit={handleSubmit}
        className="mx-auto max-w-2xl"
      >
        <div className="chat-composer-wrap">
          <div className="chat-composer flex items-end gap-2 p-2 pl-4">
            <textarea
              ref={inputRef}
              rows={1}
              disabled={disabled && !streaming}
              onKeyDown={handleKeyDown}
              onInput={autoResize}
              placeholder="Send a message…"
              className="max-h-36 min-h-[44px] flex-1 resize-none bg-transparent py-2.5 text-sm leading-relaxed text-neutral-900 outline-none placeholder:text-neutral-400 disabled:opacity-50"
            />

            {streaming ? (
              <motion.button
                type="button"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={onStop}
                className="mb-1 shrink-0 rounded-full border border-neutral-300 bg-white px-4 py-2 text-xs font-medium text-neutral-700 shadow-sm hover:bg-neutral-50"
              >
                Stop
              </motion.button>
            ) : (
              <motion.button
                type="submit"
                disabled={disabled}
                whileHover={{ scale: disabled ? 1 : 1.06 }}
                whileTap={{ scale: disabled ? 1 : 0.95 }}
                className="chat-send-btn mb-1 shrink-0"
                aria-label="Send"
              >
                ↑
              </motion.button>
            )}
          </div>
        </div>
        <p className="mt-3 text-center text-[10px] tracking-wide text-neutral-400 uppercase">
          Enter to send · Shift+Enter new line
        </p>
      </motion.form>
    </div>
  );
}
