"use client";

import { useEffect, useRef, useState } from "react";
import {
  createWorkspace,
  listWorkspaces,
  setActiveWorkspaceId,
  getActiveWorkspaceId,
} from "@/lib/api/workspaces";

export default function WorkspaceSwitcher() {
  const [items, setItems] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("personal");
  const ref = useRef(null);

  useEffect(() => {
    listWorkspaces()
      .then((data) => {
        const list = data?.items || [];
        const stored = getActiveWorkspaceId();
        const cur = stored ? Number(stored) : data?.current_id || list[0]?.id;
        if (cur && !stored) {
          setActiveWorkspaceId(cur);
        }
        setItems(list);
        setCurrentId(cur || null);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
        setCreating(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const current = items.find((w) => w.id === currentId);

  function switchTo(id) {
    if (id === currentId) {
      setOpen(false);
      return;
    }
    setActiveWorkspaceId(id);
    window.location.reload();
  }

  async function handleCreate(e) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    try {
      const ws = await createWorkspace(name, { workspace_type: newType });
      setActiveWorkspaceId(ws.id);
      window.location.reload();
    } catch {
      /* ignore */
    }
  }

  if (!items.length) return null;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="hidden max-w-[9rem] shrink-0 truncate whitespace-nowrap rounded-full border border-border px-3 py-1.5 text-xs text-muted transition-colors hover:bg-surface hover:text-foreground sm:inline-flex sm:items-center lg:max-w-[11rem]"
        title={current?.name || "Workspace"}
      >
        {current?.name || "Workspace"}
      </button>

      {open ? (
        <div className="absolute right-0 top-full z-50 mt-2 w-56 rounded-xl border border-border bg-white py-1 shadow-lg">
          {items.map((ws) => (
            <button
              key={ws.id}
              type="button"
              onClick={() => switchTo(ws.id)}
              className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface ${
                ws.id === currentId ? "font-medium text-foreground" : "text-muted"
              }`}
            >
              <span className="min-w-0 truncate">
                <span className="block truncate">{ws.name}</span>
                {ws.workspace_type ? (
                  <span className="block text-[10px] uppercase tracking-wide text-muted">
                    {ws.workspace_type}
                  </span>
                ) : null}
              </span>
              {ws.role ? (
                <span className="ml-2 shrink-0 text-[10px] uppercase text-muted">{ws.role}</span>
              ) : null}
            </button>
          ))}
          <div className="border-t border-border px-3 py-2">
            {creating ? (
              <form onSubmit={handleCreate} className="space-y-1.5">
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Workspace name"
                  className="w-full rounded-lg border border-border px-2 py-1 text-xs"
                  autoFocus
                />
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full rounded-lg border border-border px-2 py-1 text-xs text-muted"
                >
                  <option value="personal">Personal</option>
                  <option value="team">Team</option>
                  <option value="organization">Organization</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                <div className="flex gap-1">
                  <button type="submit" className="rounded-lg bg-foreground px-2 py-1 text-xs text-white">
                    Add
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCreating(false);
                      setNewName("");
                      setNewType("personal");
                    }}
                    className="rounded-lg border border-border px-2 py-1 text-xs text-muted"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setCreating(true)}
                className="text-xs text-muted hover:text-foreground"
              >
                + New workspace
              </button>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
