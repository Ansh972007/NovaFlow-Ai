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
  loading,
  open,
  onClose,
  userName,
  onLogout,
}) {
  const panel = (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center border-b border-neutral-200/70 px-4">
        <Logo size="sm" />
      </div>

      <div className="p-3">
        <motion.button
          type="button"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={onNewChat}
          disabled={!selectedAppId}
          className="chat-new-btn flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-neutral-900 disabled:opacity-40"
        >
          <span className="text-lg leading-none">+</span>
          New chat
        </motion.button>
      </div>

      <div className="px-3 pb-2">
        <p className="px-2 pb-2 text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">
          Assistants
        </p>
        {loading ? (
          <div className="space-y-2 px-1">
            {[1, 2].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded-lg bg-neutral-200/60" />
            ))}
          </div>
        ) : apps.length === 0 ? (
          <p className="px-2 py-3 text-xs leading-relaxed text-neutral-500">
            No assistants online yet.
          </p>
        ) : (
          <ul className="max-h-40 space-y-1 overflow-y-auto">
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

      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <p className="px-2 pb-2 text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">
          History
        </p>
        {sessions.length === 0 ? (
          <p className="px-2 py-2 text-xs text-neutral-500">No chats yet</p>
        ) : (
          <ul className="space-y-1">
            {sessions.map((session, i) => (
              <motion.li
                key={session.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03, duration: 0.3 }}
              >
                <button
                  type="button"
                  onClick={() => {
                    onSelectSession(session);
                    onClose?.();
                  }}
                  className={`chat-nav-item flex-col !items-start gap-0.5 ${
                    selectedSessionId === session.id ? "chat-nav-item--active" : ""
                  }`}
                >
                  <span className="w-full truncate text-left">
                    {truncate(session.title || "New chat", 36)}
                  </span>
                  <span className="text-[10px] font-normal text-neutral-400">
                    {formatWhen(session.updatedAt)}
                  </span>
                </button>
              </motion.li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-auto border-t border-neutral-200/70 p-3">
        {userName && (
          <p className="mb-2 truncate px-2 text-xs text-neutral-500">{userName}</p>
        )}
        <div className="flex gap-1">
          <Link
            href="/dashboard"
            className="flex-1 rounded-lg py-2 text-center text-[11px] font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            Dashboard
          </Link>
          <button
            type="button"
            onClick={onLogout}
            className="flex-1 rounded-lg py-2 text-center text-[11px] font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-30 bg-black/25 backdrop-blur-[2px] md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`chat-sidebar relative z-20 fixed inset-y-0 left-0 w-[17.5rem] transition-transform duration-300 ease-out md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {panel}
      </aside>
    </>
  );
}
