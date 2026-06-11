export const runtime = "nodejs";
export const dynamic = "force-static";

/**
 * GET /docs — Scalar API Reference UI, loading the spec from /openapi.json.
 * The Scalar bundle is loaded from a PINNED jsDelivr version with Subresource
 * Integrity (sha384) + crossorigin, so a CDN compromise cannot substitute the
 * script (hash mismatch -> the browser refuses to execute it).
 */
const SCALAR_SRC = "https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.59.2/dist/browser/standalone.js";
const SCALAR_SRI = "sha384-qdTNFfkRv/L0BHDvwW9XzQxu3rtN4r41Oun6L7siNlsqDTGlEKX1MYgNfNoRZ4Qg";

const HTML = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MIE API (v2) — Reference</title>
    <link rel="icon" href="data:," />
  </head>
  <body>
    <script
      id="api-reference"
      data-url="/openapi.json"
      data-configuration='{"theme":"purple","layout":"modern"}'
    ></script>
    <script src="${SCALAR_SRC}" integrity="${SCALAR_SRI}" crossorigin="anonymous"></script>
  </body>
</html>`;

export async function GET() {
  return new Response(HTML, {
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}
