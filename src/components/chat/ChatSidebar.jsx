"use client";

import { truncate } from "@/lib/utils";

export default function ChatSidebar({
  apps,
  sessions,
  selectedAppId,
  selectedSessionId,
  onSelectApp,
  onSelectSession,
  onNewChat,
  loading,
}) {
  return (
    <aside className="relative z-10 flex w-full flex-col border-r border-border/80 bg-white/70 backdrop-blur-xl md:w-72 lg:w-80">
      <div className="border-b border-border p-4">
        <button
          type="button"
          onClick={onNewChat}
          disabled={!selectedAppId}
          className="btn-primary w-full !py-2.5 text-sm disabled:opacity-40"
        >
          + New chat
        </button>
      </div>

      <div className="border-b border-border p-4">
        <p className="mb-3 flex items-center gap-2 text-[10px] font-semibold tracking-widest text-muted uppercase">
          <span className="h-1 w-1 rounded-full bg-black" />
          Assistants
        </p>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-9 animate-pulse rounded-lg bg-white" />
            ))}
          </div>
        ) : apps.length === 0 ? (
          <p className="text-sm text-muted">
            No apps online. Publish an assistant in the backend.
          </p>
        ) : (
          <ul className="max-h-40 space-y-1 overflow-y-auto">
            {apps.map((app) => (
              <li key={app.id}>
                <button
                  type="button"
                  onClick={() => onSelectApp(app)}
                  className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-200 ${
                    selectedAppId === app.id
                      ? "bg-black font-medium text-white shadow-md shadow-black/10"
                      : "hover:bg-white hover:shadow-sm"
                  }`}
                >
                  {app.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <p className="mb-3 flex items-center gap-2 text-[10px] font-semibold tracking-widest text-muted uppercase">
          <span className="h-1 w-1 rounded-full bg-black" />
          History
        </p>
        {sessions.length === 0 ? (
          <p className="text-sm text-muted">No chats yet</p>
        ) : (
          <ul className="space-y-1">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  type="button"
                  onClick={() => onSelectSession(session)}
                  className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-200 ${
                    selectedSessionId === session.id
                      ? "bg-black font-medium text-white shadow-md shadow-black/10"
                      : "hover:bg-white hover:shadow-sm"
                  }`}
                >
                  {truncate(session.title || "New chat")}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
