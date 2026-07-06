"use client";

import WorkflowCanvas from "./WorkflowCanvas";

export default function WorkflowDiffSplit({ fromLabel, toLabel, fromGraph, toGraph, overlay }) {
  return (
    <div className="flex h-full min-h-[480px] flex-col gap-2 lg:flex-row">
      <div className="workspace-panel flex min-h-[360px] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl">
        <div className="shrink-0 border-b border-neutral-200/80 bg-white/70 px-4 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-400">Before</p>
          <p className="text-sm font-semibold text-neutral-900">{fromLabel}</p>
        </div>
        <div className="relative min-h-0 flex-1">
          <WorkflowCanvas graph={fromGraph || { nodes: [], edges: [] }} readOnly />
        </div>
      </div>
      <div className="workspace-panel flex min-h-[360px] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl">
        <div className="shrink-0 border-b border-neutral-200/80 bg-white/70 px-4 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-400">After</p>
          <p className="text-sm font-semibold text-neutral-900">{toLabel}</p>
        </div>
        <div className="relative min-h-0 flex-1">
          <WorkflowCanvas
            graph={toGraph || { nodes: [], edges: [] }}
            readOnly
            diffOverlay={overlay || null}
          />
        </div>
      </div>
    </div>
  );
}
