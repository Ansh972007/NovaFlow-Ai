import Link from "next/link";

export default function DocsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <Link href="/" className="text-sm text-nova-muted hover:text-foreground">
        ← Back home
      </Link>
      <h1 className="mt-6 text-3xl font-bold">Documentation</h1>
      <p className="mt-4 text-nova-muted">
        Full docs are in the <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">docs/</code>{" "}
        folder. Quick start:
      </p>
      <ol className="mt-6 list-decimal space-y-3 pl-5 text-sm leading-relaxed">
        <li>Start Bisheng backend (or NovaFlow API) on port 3001</li>
        <li>Copy <code>.env.example</code> to <code>.env.local</code></li>
        <li>Run <code>npm run dev</code> — app on port 3000</li>
        <li>Open <Link href="/login" className="text-indigo-600 underline">/login</Link> and sign in</li>
      </ol>
    </div>
  );
}
