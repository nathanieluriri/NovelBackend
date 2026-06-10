import { HttpError } from "./errors";
import { errorResponse, successBody } from "./envelope";

/**
 * withRoute() — the single place plain handler results become the v2 envelope,
 * mirroring the legacy EnvelopeAPIRoute + v2 exception handlers
 * (see ../nextjs-migration/schema.md §1–2, architecture.md).
 *
 * Handler contract:
 *  - return a plain value           → wrapped as {success:true, message:"Success", data}
 *  - return alreadyEnveloped object → passed through untouched
 *  - return legacy {status_code, data, detail} → unwrapped (data→data, detail→message)
 *  - return a Response              → passed through raw (redirects, custom status, webhooks)
 *  - throw HttpError                → error envelope with its status/message/errors
 *  - throw anything else            → 500 "Internal Server Error"
 */

type Ctx = { params: Promise<Record<string, string>> };
type Handler = (req: Request, ctx: Ctx) => Promise<unknown>;

function isEnveloped(v: unknown): v is Record<string, unknown> {
  return (
    typeof v === "object" && v !== null && !Array.isArray(v) &&
    "success" in v && "message" in v && "data" in v
  );
}

function isLegacyApiResponse(v: unknown): v is { status_code: number; data: unknown; detail?: unknown } {
  return (
    typeof v === "object" && v !== null && !Array.isArray(v) &&
    "status_code" in v && "data" in v && "detail" in v
  );
}

export function withRoute(handler: Handler, { status = 200 }: { status?: number } = {}) {
  return async (req: Request, ctx: Ctx): Promise<Response> => {
    try {
      const result = await handler(req, ctx);
      if (result instanceof Response) return result;
      if (result === undefined || status === 204) return new Response(null, { status: 204 });
      if (isEnveloped(result)) return Response.json(result, { status });
      if (isLegacyApiResponse(result)) {
        const message = typeof result.detail === "string" && result.detail ? result.detail : "Success";
        return Response.json(successBody(result.data, message), { status });
      }
      return Response.json(successBody(result), { status });
    } catch (err) {
      if (err instanceof HttpError) {
        if (typeof err.errors === "object" && err.errors !== null) {
          return errorResponse(err.status, err.message, err.errors);
        }
        return errorResponse(err.status, err.message);
      }
      console.error("Unhandled route error:", err);
      return errorResponse(500, "Internal Server Error");
    }
  };
}
