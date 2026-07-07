"use client";

export default function WorkspaceAlert({ type = "info", children, className = "" }) {
  if (!children) return null;
  const styles =
    type === "success"
      ? "border-emerald-200/80 bg-emerald-50/90 text-emerald-800"
      : type === "error"
        ? "border-red-200/80 bg-red-50/90 text-red-800"
        : type === "warn"
          ? "border-amber-200/80 bg-amber-50/90 text-amber-900"
          : "border-neutral-200/80 bg-neutral-50/90 text-neutral-700";
  return (
    <p className={`workspace-alert rounded-xl border px-4 py-3 text-sm ${styles} ${className}`}>{children}</p>
  );
}
