import Link from "next/link";

export default function Logo({ size = "md", variant = "light", href = "/", className = "" }) {
  const sizes = {
    sm: { icon: "h-8 w-8 text-xs", text: "text-base" },
    md: { icon: "h-9 w-9 text-sm", text: "text-lg" },
    lg: { icon: "h-11 w-11 text-base", text: "text-2xl" },
  };
  const s = sizes[size] || sizes.md;
  const isDark = variant === "dark";

  return (
    <Link href={href} className={`group flex items-center gap-3 ${className}`.trim()}>
      <span
        className={`${s.icon} flex items-center justify-center rounded-full font-bold transition-transform duration-300 group-hover:scale-105 ${
          isDark
            ? "bg-white text-black"
            : "bg-black text-white"
        }`}
      >
        NF
      </span>
      <span
        className={`${s.text} font-semibold tracking-tight ${
          isDark ? "text-white" : "text-foreground"
        }`}
      >
        NovaFlow{" "}
        <span className={isDark ? "text-neutral-400" : "text-muted"}>AI</span>
      </span>
    </Link>
  );
}
