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
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  return (
    <div className="chat-composer-bar shrink-0 border-t border-neutral-200/60 bg-white/70 px-4 py-4 backdrop-blur-xl sm:px-6 sm:py-5">
      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        onSubmit={handleSubmit}
        className="mx-auto max-w-3xl"
      >
        <div className="chat-composer-wrap">
          <div className="chat-composer flex items-end gap-2 p-2 pl-4">
            <textarea
              ref={inputRef}
              rows={1}
              disabled={disabled && !streaming}
              onKeyDown={handleKeyDown}
              onInput={autoResize}
              placeholder="Message your assistant…"
              className="max-h-40 min-h-[48px] flex-1 resize-none bg-transparent py-3 text-sm leading-relaxed text-neutral-900 outline-none placeholder:text-neutral-400 disabled:opacity-50"
            />

            {streaming ? (
              <motion.button
                type="button"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={onStop}
                className="mb-1 shrink-0 rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-xs font-semibold text-neutral-700 shadow-sm hover:bg-neutral-50"
              >
                Stop
              </motion.button>
            ) : (
              <motion.button
                type="submit"
                disabled={disabled}
                whileHover={{ scale: disabled ? 1 : 1.05 }}
                whileTap={{ scale: disabled ? 1 : 0.95 }}
                className="chat-send-btn mb-1 shrink-0"
                aria-label="Send message"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </motion.button>
            )}
          </div>
        </div>
        <p className="mt-2.5 text-center text-[10px] font-medium tracking-wide text-neutral-400 uppercase">
          Enter to send · Shift+Enter for new line
        </p>
      </motion.form>
    </div>
  );
}
