"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import Logo from "@/components/Logo";
import { truncate } from "@/lib/utils";

function formatWhen(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  const diff = Date.now() - d;
  if (diff < 86400000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (diff < 604800000) return d.toLocaleDateString([], { weekday: "short" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function ChatSidebar({
  apps,
  sessions,
  selectedAppId,
  selectedSessionId,
  onSelectApp,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  loading,
  open,
  onClose,
}) {
  const canNewChat = !loading && apps.length > 0;

  const panel = (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center border-b border-neutral-200/70 px-4">
        <Logo size="sm" href="/dashboard" />
      </div>

      <div className="p-3">
        <motion.button
          type="button"
          whileHover={{ scale: canNewChat ? 1.01 : 1 }}
          whileTap={{ scale: canNewChat ? 0.99 : 1 }}
          onClick={() => {
            if (!canNewChat) return;
            onNewChat();
            onClose?.();
          }}
          disabled={!canNewChat}
          className="chat-new-btn flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-neutral-900 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <span className="text-lg leading-none">+</span>
          New chat
        </motion.button>
      </div>

      <div className="px-3 pb-2">
        <p className="px-2 pb-2 text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">
          Interfaces
        </p>
        {loading ? (
          <div className="space-y-2 px-1">
            {[1, 2].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded-lg bg-neutral-200/60" />
            ))}
          </div>
        ) : apps.length === 0 ? (
          <p className="px-2 py-3 text-xs leading-relaxed text-neutral-500">
            No interfaces online yet.{" "}
            <Link href="/projects?tab=assistants" className="font-medium text-neutral-800 underline-offset-2 hover:underline">
              Create one
            </Link>
          </p>
        ) : (
          <ul className="max-h-44 space-y-1 overflow-y-auto">
            {apps.map((app) => (
              <li key={app.id}>
                <button
                  type="button"
                  onClick={() => {
                    onSelectApp(app);
                    onClose?.();
                  }}
                  className={`chat-nav-item ${selectedAppId === app.id ? "chat-nav-item--active" : ""}`}
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-neutral-900 text-[9px] font-bold text-white">
                    AI
                  </span>
                  <span className="truncate">{app.name}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4">
        <p className="px-2 pb-2 text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">
          History
        </p>
        {sessions.length === 0 ? (
          <p className="px-2 py-2 text-xs text-neutral-500">No chats yet — start a new conversation.</p>
        ) : (
          <ul className="space-y-1">
            {sessions.map((session, i) => (
              <motion.li
                key={session.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03, duration: 0.3 }}
                className="group/session relative flex items-center"
              >
                <button
                  type="button"
                  onClick={() => {
                    onSelectSession(session);
                    onClose?.();
                  }}
                  className={`chat-nav-item flex-1 flex-col !items-start gap-0.5 pr-8 ${
                    selectedSessionId === session.id ? "chat-nav-item--active" : ""
                  }`}
                >
                  <span className="w-full truncate text-left">
                    {truncate(session.title || "New chat", 32)}
                  </span>
                  <span className="text-[10px] font-normal text-neutral-400">
                    {formatWhen(session.updatedAt)}
                  </span>
                </button>
                {onDeleteSession && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    title="Delete chat session"
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-neutral-400 opacity-0 hover:bg-red-50 hover:text-red-600 transition-all group-hover/session:opacity-100"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </motion.li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-30 bg-black/25 backdrop-blur-[2px] lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`chat-sidebar relative z-20 fixed inset-y-0 left-0 w-[17.5rem] transition-transform duration-300 ease-out lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {panel}
      </aside>
    </>
  );
}
