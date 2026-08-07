import { useCallback, useEffect, useState } from "react";
import {
  getActiveWorkspaceId,
  isWorkspaceReadOnly,
  listWorkspaces,
  workspaceCanEdit,
  workspaceCanRun,
} from "@/lib/api/workspaces";

export function useWorkspaceAccess() {
  const [role, setRole] = useState("editor");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await listWorkspaces();
      const id = getActiveWorkspaceId() || data?.current_id;
      const item = (data?.items || []).find((w) => String(w.id) === String(id));
      setRole(item?.role || "editor");
    } catch {
      setRole("editor");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    role,
    loading,
    readOnly: isWorkspaceReadOnly(role),
    canEdit: workspaceCanEdit(role),
    canRun: workspaceCanRun(role),
    refresh,
  };
}
