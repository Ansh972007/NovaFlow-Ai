"use client";

import { memo } from "react";
import WorkspaceLoading from "@/components/workspace/WorkspaceLoading";

function WorkspacePageLoading({ message }) {
  return <WorkspaceLoading message={message} />;
}

export default memo(WorkspacePageLoading);
