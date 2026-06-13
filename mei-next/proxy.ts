import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * TEMPORARY — CORS disabled (allow all origins) on /api/*.
 *
 * This reflects whatever Origin the browser sends and allows credentials,
 * effectively turning CORS enforcement off for cross-origin callers.
 *
 * ⚠️ Remove this file (or lock `allowOrigin` down to a real allowlist)
 *    before shipping anything beyond local/dev use.
 *
 * In Next.js 16 the `middleware` file convention was renamed to `proxy`,
 * so CORS for API routes lives here. See
 * node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md
 */

const corsOptions = {
  "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Allow-Credentials": "true",
};

export function proxy(request: NextRequest) {
  // Reflect the caller's origin. A bare "*" can't be combined with
  // credentials, so we echo the request Origin to allow everyone.
  const allowOrigin = request.headers.get("origin") ?? "*";

  // Preflight (OPTIONS) — answer it directly.
  if (request.method === "OPTIONS") {
    return NextResponse.json(
      {},
      {
        headers: {
          "Access-Control-Allow-Origin": allowOrigin,
          ...corsOptions,
        },
      },
    );
  }

  // Simple/actual requests — attach CORS headers to the response.
  const response = NextResponse.next();
  response.headers.set("Access-Control-Allow-Origin", allowOrigin);
  for (const [key, value] of Object.entries(corsOptions)) {
    response.headers.set(key, value);
  }
  return response;
}

export const config = {
  matcher: "/api/:path*",
};
