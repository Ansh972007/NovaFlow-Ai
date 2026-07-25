"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getActiveWorkspaceId } from "@/lib/api/workspaces";
import {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  deleteNotification,
  clearAllNotifications,
} from "@/lib/api/notifications";

export default function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [filterUnread, setFilterUnread] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const dropdownRef = useRef(null);
  const wsRef = useRef(null);

  const workspaceId = typeof window !== "undefined" ? getActiveWorkspaceId() : null;

  // Load notifications from HTTP API
  async function loadData() {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const countData = await getUnreadCount(workspaceId);
      setUnreadCount(countData?.unread_count || 0);

      const listData = await getNotifications(workspaceId, { limit: 30 });
      setNotifications(listData?.rows || []);
    } catch (err) {
      setError(err.message || "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }

  // WebSocket Connection Lifecycle with auto-reconnect
  useEffect(() => {
    if (!workspaceId) return;
    loadData();

    let reconnectTimer = null;
    let attempts = 0;

    function connectWS() {
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {}
      }

      const token = localStorage.getItem("nf_token") || "";
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.port === "3000" ? `${window.location.hostname}:3001` : window.location.host;
      const wsUrl = `${protocol}//${host}/api/v1/notifications/ws?token=${token}&workspace_id=${workspaceId}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        attempts = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data?.type === "notification" && data.notification) {
            setNotifications((prev) => [data.notification, ...prev]);
            setUnreadCount((c) => c + 1);
          }
        } catch {}
      };

      ws.onclose = () => {
        if (reconnectTimer) clearTimeout(reconnectTimer);
        // Exponential backoff
        const delay = Math.min(1000 * Math.pow(2, attempts), 30000);
        attempts += 1;
        reconnectTimer = setTimeout(() => {
          connectWS();
        }, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connectWS();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [workspaceId]);

  // Click Outside Hook
  useEffect(() => {
    function onClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  async function handleMarkRead(id) {
    try {
      await markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: 1 } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {}
  }

  async function handleMarkAllRead() {
    if (!workspaceId) return;
    try {
      await markAllAsRead(workspaceId);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: 1 })));
      setUnreadCount(0);
    } catch {}
  }

  async function handleDelete(id, isUnread) {
    try {
      await deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (isUnread) {
        setUnreadCount((c) => Math.max(0, c - 1));
      }
    } catch {}
  }

  async function handleClearAll() {
    if (!workspaceId || !window.confirm("Clear all notifications in this workspace?")) return;
    try {
      await clearAllNotifications(workspaceId);
      setNotifications([]);
      setUnreadCount(0);
    } catch {}
  }

  const displayed = notifications.filter((n) => !filterUnread || n.is_read === 0);

  function getLevelBadgeClass(level) {
    switch (level?.toUpperCase()) {
      case "SUCCESS":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "WARNING":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "ERROR":
      case "CRITICAL":
        return "bg-red-50 text-red-700 border-red-200";
      default:
        return "bg-neutral-50 text-neutral-600 border-neutral-200";
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`relative shrink-0 items-center rounded-full p-2 transition-colors inline-flex ${
          open ? "bg-neutral-100 text-neutral-900" : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
        }`}
        title="Notifications"
        aria-label="Notifications"
        aria-expanded={open}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white shadow-sm ring-2 ring-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 sm:w-96 rounded-2xl border border-neutral-200/80 bg-white/95 py-1 shadow-2xl backdrop-blur-xl transition-all">
          <div className="flex items-center justify-between border-b border-neutral-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-neutral-900">Notifications</h3>
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="text-neutral-500 hover:text-neutral-950 font-medium"
              >
                Mark all read
              </button>
              <span className="text-neutral-300">·</span>
              <button
                type="button"
                onClick={handleClearAll}
                className="text-red-500 hover:text-red-700 font-medium"
              >
                Clear all
              </button>
            </div>
          </div>

          <div className="flex gap-2 border-b border-neutral-50 px-4 py-2">
            <button
              type="button"
              onClick={() => setFilterUnread(false)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                !filterUnread ? "bg-neutral-900 text-white" : "bg-neutral-50 text-neutral-600 hover:bg-neutral-100"
              }`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => setFilterUnread(true)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                filterUnread ? "bg-neutral-900 text-white" : "bg-neutral-50 text-neutral-600 hover:bg-neutral-100"
              }`}
            >
              Unread
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto divide-y divide-neutral-100">
            {loading && notifications.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <span className="text-xs text-neutral-400">Loading notifications…</span>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center py-8 px-4 text-center">
                <span className="text-xs text-red-500">{error}</span>
              </div>
            ) : displayed.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <svg
                  className="h-8 w-8 text-neutral-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0 1 18 14.158V11a6.002 6.002 0 0 0-4-5.659V5a2 2 0 1 0-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 1 1-6 0v-1m6 0H9" />
                </svg>
                <p className="mt-3 text-xs font-medium text-neutral-500">All caught up!</p>
                <p className="text-[10px] text-neutral-400 mt-1">
                  {filterUnread ? "No unread notifications." : "No notifications in this workspace."}
                </p>
              </div>
            ) : (
              displayed.map((n) => (
                <div
                  key={n.id}
                  className={`group relative flex items-start gap-3 p-4 transition-colors ${
                    n.is_read === 0 ? "bg-neutral-50/50 hover:bg-neutral-50" : "hover:bg-neutral-50/30"
                  }`}
                >
                  {/* Unread circle marker */}
                  <div className="flex shrink-0 items-center justify-center pt-1.5">
                    {n.is_read === 0 ? (
                      <button
                        type="button"
                        onClick={() => handleMarkRead(n.id)}
                        className="h-2 w-2 rounded-full bg-blue-500 hover:scale-125 transition-transform"
                        title="Mark as read"
                      />
                    ) : (
                      <div className="h-2 w-2 rounded-full bg-transparent" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-semibold text-neutral-900 truncate">{n.title}</p>
                      {n.category && (
                        <span
                          className={`rounded-full border px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider ${getLevelBadgeClass(
                            n.level
                          )}`}
                        >
                          {n.category}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-neutral-600 leading-relaxed break-words">{n.message}</p>
                    {n.action_url && (
                      <Link
                        href={n.action_url}
                        onClick={() => setOpen(false)}
                        className="mt-2 inline-flex items-center gap-1 text-[10px] font-semibold text-neutral-900 hover:underline"
                      >
                        View details
                        <span>→</span>
                      </Link>
                    )}
                    <p className="mt-1.5 text-[9px] text-neutral-400 tabular-nums">
                      {new Date(n.create_time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>

                  {/* Delete button */}
                  <button
                    type="button"
                    onClick={() => handleDelete(n.id, n.is_read === 0)}
                    className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-red-500 transition-all p-1"
                    title="Delete"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
