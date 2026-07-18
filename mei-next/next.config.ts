import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The frontend (and the legacy FastAPI contract) calls every endpoint WITH a
  // trailing slash, e.g. `GET /api/v2/author_room/`. By default Next.js answers
  // such a request with a 308 trailing-slash redirect — and that redirect is
  // emitted by the routing layer, so `proxy.ts` never attaches CORS headers to
  // it. A cross-origin browser then fails the CORS preflight/redirect check
  // before the real request is ever sent, surfacing as a "CORS error" / failed
  // (≈500) request even though auth and the handler are fine.
  //
  // Disabling the redirect makes the trailing-slash path resolve to the same
  // route handler directly, so `proxy.ts` can add CORS headers to the actual
  // response (preflight + GET alike). See NovelBackend issue #23.
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
