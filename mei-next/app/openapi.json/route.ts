export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { buildOpenApiSpec } from "@/lib/openapi/spec";

/**
 * GET /openapi.json — the OpenAPI 3.0 document for the v2 API.
 * `servers` is set from the request origin so "Try it out" targets this same
 * deployment (preview, prod, or a custom domain). Not enveloped.
 */
export async function GET(req: Request) {
  const origin = new URL(req.url).origin;
  return Response.json(buildOpenApiSpec(origin), {
    headers: { "cache-control": "public, max-age=300" },
  });
}
