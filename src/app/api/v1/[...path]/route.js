import { getServerApiBaseUrl } from "@/lib/api/config";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
]);

async function proxyRequest(request, context) {
  const { path: segments = [] } = await context.params;
  const path = segments.join("/");
  const base = getServerApiBaseUrl().replace(/\/$/, "");
  const incoming = new URL(request.url);
  const target = `${base}/api/v1/${path}${incoming.search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const method = request.method;
  const hasBody = method !== "GET" && method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  let upstream;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body,
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    return Response.json(
      {
        status_code: 503,
        status_message: "NovaFlow API unreachable from web server",
      },
      { status: 503 }
    );
  }

  const outHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      outHeaders.set(key, value);
    }
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const OPTIONS = proxyRequest;
