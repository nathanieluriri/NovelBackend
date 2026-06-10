export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Root health check — RAW body (not enveloped), matching the legacy root app. */
export async function GET() {
  return Response.json({ status: "healthy" });
}
