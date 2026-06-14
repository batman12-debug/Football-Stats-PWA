import { NextRequest, NextResponse } from "next/server";

import {
  buildBackendApiUrl,
  filterProxyRequestHeaders,
  filterProxyResponseHeaders,
} from "@/lib/api-proxy";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const PROXY_TIMEOUT_MS = 30_000;

type RouteContext = {
  params: { path: string[] };
};

async function proxyRequest(req: NextRequest, { params }: RouteContext): Promise<NextResponse> {
  const target = buildBackendApiUrl(params.path, req.nextUrl.search);

  if (!target) {
    return NextResponse.json(
      { error: "Backend URL is not configured or must use HTTPS on Netlify." },
      { status: 503 },
    );
  }

  const headers = filterProxyRequestHeaders(req.headers);

  const init: RequestInit = {
    method: req.method,
    headers,
    signal: AbortSignal.timeout(PROXY_TIMEOUT_MS),
    cache: "no-store",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  try {
    const upstream = await fetch(target, init);
    return new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: filterProxyResponseHeaders(upstream.headers),
    });
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const HEAD = proxyRequest;
export const OPTIONS = proxyRequest;
