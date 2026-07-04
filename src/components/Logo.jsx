import Link from "next/link";

export default function Logo({ size = "md" }) {
  const sizes = {
    sm: { icon: "h-8 w-8 text-sm", text: "text-lg" },
    md: { icon: "h-10 w-10 text-base", text: "text-xl" },
    lg: { icon: "h-12 w-12 text-lg", text: "text-2xl" },
  };
  const s = sizes[size] || sizes.md;

  return (
    <Link href="/" className="flex items-center gap-2.5 group">
      <span
        className={`${s.icon} nova-gradient flex items-center justify-center rounded-xl font-bold text-white shadow-lg shadow-indigo-500/25`}
      >
        N
      </span>
      <span className={`${s.text} font-semibold tracking-tight`}>
        NovaFlow{" "}
        <span className="nova-gradient-text font-bold">AI</span>
      </span>
    </Link>
  );
}
