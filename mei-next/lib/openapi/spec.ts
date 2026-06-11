/**
 * Builds the OpenAPI 3.0 document for the v2 API from the route inventory
 * (see ../../../nextjs-migration/endpoints.md). Served at /openapi.json and
 * rendered by the Scalar UI at /docs.
 */
import { schemas, securitySchemes } from "./schemas";

type Schema = Record<string, unknown>;
type Sec = "member" | "admin" | "any" | "none";

const ref = (n: string): Schema => ({ $ref: `#/components/schemas/${n}` });
const obj = (properties: Record<string, Schema>, required?: string[]): Schema => ({
  type: "object",
  properties,
  ...(required && required.length ? { required } : {}),
});
const arr = (items: Schema): Schema => ({ type: "array", items });
const json = (schema: Schema) => ({ "application/json": { schema } });

/** Success envelope wrapping a data schema. */
const env = (data: Schema): Schema =>
  obj({ success: { type: "boolean", enum: [true] }, message: { type: "string" }, data }, ["success", "message", "data"]);
/** Enveloped PaginatedListOut (flat items + meta + summary). */
const envPaged = (item: Schema): Schema =>
  env(obj({ items: arr(item), meta: ref("ListMeta"), summary: ref("ListSummary") }, ["items", "meta", "summary"]));
/** Enveloped indexed list ({index,item} + meta) — user-v2 likes/bookmarks only. */
const envIndexed = (item: Schema): Schema =>
  env(obj({ items: arr(obj({ index: { type: "integer" }, item }, ["index", "item"])), meta: ref("ListMeta") }, ["items", "meta"]));

const errorRef = json(ref("ErrorEnvelope"));

interface OpOpts {
  summary: string;
  tag: string;
  sec: Sec;
  desc?: string;
  path?: string[]; // path param names
  query?: string[]; // query param names (skip|limit|targetType|targetId|redirect_path|target)
  body?: string; // request-body schema name
  ok: Schema; // success response body schema
  okStatus?: number;
  redirect?: boolean; // 302 endpoints
}

function qParam(name: string): Schema {
  const base: Record<string, Schema> = {
    skip: { name: "skip", in: "query", schema: { type: "integer", default: 0, minimum: 0 } },
    limit: { name: "limit", in: "query", schema: { type: "integer", default: 20, minimum: 1, maximum: 100 } },
    targetType: { name: "targetType", in: "query", schema: { type: "string", enum: ["book", "chapter", "page"] } },
    targetId: { name: "targetId", in: "query", schema: { type: "string" } },
    target: { name: "target", in: "query", schema: { type: "string" }, description: "OAuth target alias" },
    redirect_path: { name: "redirect_path", in: "query", schema: { type: "string", maxLength: 512 } },
  };
  return base[name] ?? { name, in: "query", schema: { type: "string" } };
}

function operation(o: OpOpts): Schema {
  const op: Schema = { tags: [o.tag], summary: o.summary };
  if (o.desc) op.description = o.desc;
  if (o.sec !== "none") {
    op.security = [{ bearerAuth: [] }];
    const note = o.sec === "admin" ? "Admin token required." : o.sec === "any" ? "Member or admin token." : "Member token required.";
    op.description = (o.desc ? o.desc + " " : "") + note;
  }
  const parameters: Schema[] = [];
  for (const p of o.path ?? []) parameters.push({ name: p, in: "path", required: true, schema: { type: "string" } });
  for (const q of o.query ?? []) parameters.push(qParam(q));
  if (parameters.length) op.parameters = parameters;
  if (o.body) op.requestBody = { required: true, content: json(ref(o.body)) };

  const okStatus = String(o.okStatus ?? 200);
  const responses: Record<string, Schema> = o.redirect
    ? { "302": { description: "Redirect to Google / the frontend target" } }
    : { [okStatus]: { description: "Success", content: json(o.ok) } };
  if (!o.redirect) {
    responses["400"] = { description: "Bad request", content: errorRef };
    responses["404"] = { description: "Not found", content: errorRef };
    responses["422"] = { description: "Validation error", content: errorRef };
    if (o.sec !== "none") {
      responses["401"] = { description: "Invalid/expired token", content: errorRef };
      responses["403"] = { description: "Missing Authorization header / forbidden", content: errorRef };
    }
  }
  op.responses = responses;
  return op;
}

type Route = [method: string, path: string, opts: OpOpts];

const ROUTES: Route[] = [
  // ---- System --------------------------------------------------------------
  ["get", "/health", { summary: "Liveness check (not enveloped)", tag: "System", sec: "none", ok: ref("HealthOut") }],

  // ---- User ----------------------------------------------------------------
  ["get", "/api/v2/user/details", { summary: "Aggregated user details", tag: "User", sec: "member", ok: env(ref("UserDetailsV2Out")) }],
  ["get", "/api/v2/user/likes", { summary: "My likes (indexed, paginated)", tag: "User", sec: "member", query: ["skip", "limit"], ok: envIndexed(ref("LikeOut")) }],
  ["get", "/api/v2/user/bookmarks", { summary: "My bookmarks (indexed, paginated)", tag: "User", sec: "member", query: ["skip", "limit"], ok: envIndexed(ref("BookMarkOut")) }],
  ["get", "/api/v2/user/reading/progress", { summary: "My reading progress", tag: "User", sec: "member", ok: env(ref("ReadingProgressOut")) }],
  ["post", "/api/v2/user/sign-up", { summary: "Register (credentials)", tag: "User", sec: "none", body: "NewUserBase", ok: env(ref("NewUserOut")) }],
  ["post", "/api/v2/user/sign-in", { summary: "Login (credentials)", tag: "User", sec: "none", body: "OldUserBase", ok: env(ref("OldUserOut")) }],
  ["post", "/api/v2/user/refresh", { summary: "Refresh access+refresh tokens", tag: "User", sec: "none", desc: "Send the (expired) access JWT in Authorization plus the refresh token in the body.", body: "RefreshTokenRequest", ok: env(ref("TokenRefreshOut")) }],
  ["get", "/api/v2/user/google/auth", { summary: "Start Google OAuth", tag: "User", sec: "none", query: ["target", "redirect_path"], ok: ref("MessageOut"), redirect: true }],
  ["get", "/api/v2/user/google/callback", { summary: "Google OAuth callback", tag: "User", sec: "none", ok: ref("MessageOut"), redirect: true }],
  ["get", "/api/v2/user/auth/callback", { summary: "Google OAuth callback (alias)", tag: "User", sec: "none", ok: ref("MessageOut"), redirect: true }],
  ["post", "/api/v2/user/google/exchange", { summary: "Exchange one-time OAuth code for tokens", tag: "User", sec: "none", body: "GoogleExchangeRequest", ok: env(ref("OldUserOut")) }],
  ["post", "/api/v2/user/initiate/change-password", { summary: "Send password-reset OTP", tag: "User", sec: "none", body: "EmailBody", ok: env(ref("MessageOut")) }],
  ["post", "/api/v2/user/conclude/change-password", { summary: "Complete password reset", tag: "User", sec: "none", body: "ConcludePasswordBody", ok: env(ref("MessageOut")) }],
  ["patch", "/api/v2/user/update", { summary: "Update my profile", tag: "User", sec: "member", body: "UserUpdate", ok: env(ref("NewUserOut")) }],
  ["get", "/api/v2/user/all/user-details", { summary: "List all users", tag: "User", sec: "admin", ok: env(arr(ref("UserOut"))) }],
  ["get", "/api/v2/user/{userId}/user-details", { summary: "User details with chapter read-flags", tag: "User", sec: "admin", path: ["userId"], ok: env(ref("UserOutChapterDetails")) }],
  ["patch", "/api/v2/user/{userId}/status/{new_status}", { summary: "Change user status", tag: "User", sec: "admin", path: ["userId", "new_status"], ok: env(ref("MessageOut")) }],

  // ---- Admin ---------------------------------------------------------------
  ["post", "/api/v2/admin/invite", { summary: "Invite an admin", tag: "Admin", sec: "admin", body: "InviteBody", ok: env(ref("MessageOut")) }],
  ["post", "/api/v2/admin/sign-up", { summary: "Admin register (invite-gated)", tag: "Admin", sec: "none", body: "NewAdminCreate", ok: env(ref("NewAdminOut")) }],
  ["post", "/api/v2/admin/sign-in", { summary: "Admin login (issues inactive token + OTP email)", tag: "Admin", sec: "none", body: "AdminBase", ok: env(ref("NewAdminOut")) }],
  ["post", "/api/v2/admin/verify", { summary: "Verify admin OTP (activates token)", tag: "Admin", sec: "none", body: "VerificationRequest", ok: env(ref("MessageOut")) }],
  ["post", "/api/v2/admin/refresh", { summary: "Refresh admin tokens", tag: "Admin", sec: "none", body: "RefreshTokenRequest", ok: env(ref("TokenRefreshOut")) }],
  ["post", "/api/v2/admin/initiate/change-password", { summary: "Send admin password-reset OTP", tag: "Admin", sec: "none", body: "EmailBody", ok: env(ref("MessageOut")) }],
  ["post", "/api/v2/admin/conclude/change-password", { summary: "Complete admin password reset", tag: "Admin", sec: "none", body: "ConcludePasswordBody", ok: env(ref("MessageOut")) }],
  ["get", "/api/v2/admin/details", { summary: "My admin details", tag: "Admin", sec: "admin", ok: env(ref("NewAdminOut")) }],
  ["get", "/api/v2/admin/all/details", { summary: "List all admins", tag: "Admin", sec: "admin", ok: env(arr(ref("NewAdminOut"))) }],
  ["patch", "/api/v2/admin/update", { summary: "Update admin profile", tag: "Admin", sec: "admin", body: "AdminUpdate", ok: env(ref("NewAdminOut")) }],
  ["get", "/api/v2/admin/dashboardAnalytics", { summary: "Dashboard analytics", tag: "Admin", sec: "admin", ok: env(ref("AdminDashboardAnalytics")) }],

  // ---- Book (all admin) ----------------------------------------------------
  ["get", "/api/v2/book/get", { summary: "List books", tag: "Book", sec: "admin", query: ["skip", "limit"], ok: envPaged(ref("BookOut")) }],
  ["post", "/api/v2/book/create", { summary: "Create book", tag: "Book", sec: "admin", body: "BookBaseRequest", ok: env(ref("BookOut")) }],
  ["delete", "/api/v2/book/delete/{bookId}", { summary: "Delete book (cascades)", tag: "Book", sec: "admin", path: ["bookId"], ok: env(ref("BookOut")) }],
  ["patch", "/api/v2/book/update/{bookId}", { summary: "Update book", tag: "Book", sec: "admin", path: ["bookId"], body: "BookUpdate", ok: env(ref("BookOut")) }],

  // ---- Chapter -------------------------------------------------------------
  ["get", "/api/v2/chapter/admin/get/allChapters/{bookId}", { summary: "List chapters (admin)", tag: "Chapter", sec: "admin", path: ["bookId"], query: ["skip", "limit"], ok: envPaged(ref("ChapterOut")) }],
  ["get", "/api/v2/chapter/user/get/allChapters/{bookId}", { summary: "List chapters (reader)", tag: "Chapter", sec: "any", path: ["bookId"], query: ["skip", "limit"], ok: envPaged(ref("ChapterOut")) }],
  ["get", "/api/v2/chapter/admin/get/chapterId/{chapterId}", { summary: "Get chapter by id (admin)", tag: "Chapter", sec: "admin", path: ["chapterId"], ok: env(ref("ChapterOut")) }],
  ["get", "/api/v2/chapter/admin/get/{bookId}/{chapterNumber}", { summary: "Get chapter by number (public)", tag: "Chapter", sec: "none", path: ["bookId", "chapterNumber"], ok: env(ref("ChapterOut")) }],
  ["get", "/api/v2/chapter/user/get/chapterId/{chapterId}", { summary: "Get chapter by id (reader)", tag: "Chapter", sec: "any", path: ["chapterId"], ok: env(ref("ChapterOut")) }],
  ["get", "/api/v2/chapter/user/get/{bookId}/{chapterNumber}", { summary: "Get chapter by number (reader)", tag: "Chapter", sec: "any", path: ["bookId", "chapterNumber"], ok: env(ref("ChapterOut")) }],
  ["post", "/api/v2/chapter/create", { summary: "Create chapter", tag: "Chapter", sec: "admin", body: "ChapterBaseRequest", ok: env(ref("ChapterOut")) }],
  ["delete", "/api/v2/chapter/delete/{chapterId}", { summary: "Delete chapter (cascades pages)", tag: "Chapter", sec: "admin", path: ["chapterId"], ok: env(ref("ChapterOut")) }],
  ["patch", "/api/v2/chapter/update/{chapterId}", { summary: "Update chapter", tag: "Chapter", sec: "admin", path: ["chapterId"], body: "ChapterUpdateRequest", ok: env(ref("ChapterOut")) }],

  // ---- Page ----------------------------------------------------------------
  ["get", "/api/v2/page/get/{chapterId}", { summary: "List pages of a chapter", tag: "Page", sec: "any", path: ["chapterId"], query: ["skip", "limit"], ok: envPaged(ref("PageOut")) }],
  ["get", "/api/v2/page/get/page/{pageId}", { summary: "Get a page (tracks reading progress for members)", tag: "Page", sec: "any", path: ["pageId"], ok: env(ref("PageOut")) }],
  ["post", "/api/v2/page/create/{bookId}", { summary: "Create page", tag: "Page", sec: "admin", path: ["bookId"], body: "PageBase", ok: env(ref("PageOut")) }],
  ["delete", "/api/v2/page/delete/{pageId}", { summary: "Delete page", tag: "Page", sec: "admin", path: ["pageId"], ok: env(ref("MessageOut")) }],
  ["patch", "/api/v2/page/update/{pageId}", { summary: "Update page", tag: "Page", sec: "admin", path: ["pageId"], body: "PageUpdateRequest", ok: env(ref("PageOut")) }],

  // ---- Bookmark ------------------------------------------------------------
  ["get", "/api/v2/bookmark/get", { summary: "My bookmarks", tag: "Bookmark", sec: "any", query: ["targetType", "skip", "limit"], ok: envPaged(ref("BookMarkOut")) }],
  ["get", "/api/v2/bookmark/get/{userId}", { summary: "Bookmarks for a user (self only)", tag: "Bookmark", sec: "any", path: ["userId"], query: ["targetType", "skip", "limit"], ok: envPaged(ref("BookMarkOut")) }],
  ["post", "/api/v2/bookmark/create", { summary: "Create bookmark", tag: "Bookmark", sec: "any", body: "BookMarkCreateRequest", ok: env(ref("BookMarkOut")) }],
  ["delete", "/api/v2/bookmark/remove/{bookmarkId}", { summary: "Remove bookmark", tag: "Bookmark", sec: "any", path: ["bookmarkId"], ok: env(ref("BookMarkOut")) }],

  // ---- Like ----------------------------------------------------------------
  ["get", "/api/v2/like/get", { summary: "My likes", tag: "Like", sec: "any", query: ["skip", "limit"], ok: envPaged(ref("LikeOut")) }],
  ["get", "/api/v2/like/get/{chapterId}", { summary: "Likes on a chapter (with users)", tag: "Like", sec: "none", path: ["chapterId"], query: ["skip", "limit"], ok: envPaged(ref("LikeWithUserOut")) }],
  ["get", "/api/v2/like/admin/get/chapter/{chapterId}/users", { summary: "Users who liked a chapter", tag: "Like", sec: "admin", path: ["chapterId"], query: ["skip", "limit"], ok: envPaged(ref("ChapterInteractionUserOut")) }],
  ["post", "/api/v2/like/create", { summary: "Like a chapter", tag: "Like", sec: "any", body: "LikeBaseRequest", ok: env(ref("LikeOut")) }],
  ["delete", "/api/v2/like/remove/{likeId}", { summary: "Remove a like", tag: "Like", sec: "none", path: ["likeId"], ok: env(ref("LikeOut")) }],

  // ---- Comment -------------------------------------------------------------
  ["get", "/api/v2/comment/get", { summary: "Comments by target (or mine)", tag: "Comment", sec: "any", query: ["targetType", "targetId", "skip", "limit"], ok: envPaged(ref("CommentOut")) }],
  ["get", "/api/v2/comment/get/target/{targetType}/{targetId}", { summary: "Comments by target", tag: "Comment", sec: "none", path: ["targetType", "targetId"], query: ["skip", "limit"], ok: envPaged(ref("CommentOut")) }],
  ["get", "/api/v2/comment/get/{chapterId}", { summary: "Comments on a chapter (legacy)", tag: "Comment", sec: "none", path: ["chapterId"], query: ["skip", "limit"], ok: envPaged(ref("CommentOut")) }],
  ["get", "/api/v2/comment/admin/get/chapter/{chapterId}/users", { summary: "Users who commented on a chapter", tag: "Comment", sec: "admin", path: ["chapterId"], query: ["skip", "limit"], ok: envPaged(ref("ChapterInteractionUserOut")) }],
  ["post", "/api/v2/comment/create", { summary: "Create comment", tag: "Comment", sec: "any", body: "CommentCreateRequest", ok: env(ref("CommentOut")) }],
  ["delete", "/api/v2/comment/user/remove/{commentId}", { summary: "Remove my comment", tag: "Comment", sec: "any", path: ["commentId"], ok: env(ref("CommentOut")) }],
  ["delete", "/api/v2/comment/admin/remove/{commentId}", { summary: "Remove any comment (admin)", tag: "Comment", sec: "admin", path: ["commentId"], ok: env(ref("CommentOut")) }],
  ["patch", "/api/v2/comment/update", { summary: "Edit a comment", tag: "Comment", sec: "any", body: "UpdateCommentBaseRequest", ok: env(ref("CommentOut")) }],

  // ---- Author rooms --------------------------------------------------------
  ["get", "/api/v2/author_room/", { summary: "List author rooms", tag: "AuthorRoom", sec: "member", query: ["skip", "limit"], ok: envPaged(ref("AuthorRoomOut")) }],
  ["post", "/api/v2/author_room/", { summary: "Create author room", tag: "AuthorRoom", sec: "any", body: "AuthorRoomBase", ok: env(ref("AuthorRoomOut")), okStatus: 201 }],
  ["get", "/api/v2/author_room/{id}", { summary: "Get author room", tag: "AuthorRoom", sec: "member", path: ["id"], ok: env(ref("AuthorRoomOut")) }],
  ["patch", "/api/v2/author_room/{id}", { summary: "Update author room", tag: "AuthorRoom", sec: "any", path: ["id"], body: "AuthorRoomUpdate", ok: env(ref("AuthorRoomOut")) }],
  ["delete", "/api/v2/author_room/{id}", { summary: "Delete author room (admin)", tag: "AuthorRoom", sec: "admin", path: ["id"], ok: env(ref("DeletedOut")) }],

  // ---- Reactions -----------------------------------------------------------
  ["get", "/api/v2/reactions/", { summary: "List reactions", tag: "Reactions", sec: "none", query: ["skip", "limit"], ok: envPaged(ref("ReactionOut")) }],
  ["post", "/api/v2/reactions/", { summary: "Create reaction", tag: "Reactions", sec: "member", body: "ReactionBase", ok: env(ref("ReactionOut")), okStatus: 201 }],
  ["get", "/api/v2/reactions/{authorRoomId}", { summary: "My reaction for a room", tag: "Reactions", sec: "member", path: ["authorRoomId"], ok: env(ref("ReactionOut")) }],
  ["patch", "/api/v2/reactions/{authorRoomId}", { summary: "Update my reaction", tag: "Reactions", sec: "member", path: ["authorRoomId"], body: "ReactionUpdate", ok: env(ref("ReactionOut")) }],
  ["delete", "/api/v2/reactions/{authorRoomId}", { summary: "Delete my reaction", tag: "Reactions", sec: "member", path: ["authorRoomId"], ok: env({ type: "object", nullable: true }) }],

  // ---- Payments ------------------------------------------------------------
  ["get", "/api/v2/payment/get-payment-bundles", { summary: "List payment bundles", tag: "Payment", sec: "any", query: ["skip", "limit"], ok: envPaged(ref("PaymentBundlesOut")) }],
  ["get", "/api/v2/payment/pricing", { summary: "Pricing catalog", tag: "Payment", sec: "any", ok: env(ref("PricingCatalogOut")) }],
  ["post", "/api/v2/payment/create-payment-bundle", { summary: "Create a bundle", tag: "Payment", sec: "admin", body: "PaymentBundles", ok: env(ref("PaymentBundlesOut")) }],
  ["patch", "/api/v2/payment/update-payment-bundle/{bundleId}", { summary: "Update a bundle", tag: "Payment", sec: "admin", path: ["bundleId"], body: "PaymentBundlesUpdate", ok: env(ref("MessageOut")) }],
  ["delete", "/api/v2/payment/delete-payment-bundle/{bundleId}", { summary: "Delete a bundle", tag: "Payment", sec: "admin", path: ["bundleId"], ok: env(ref("MessageOut")) }],
  ["post", "/api/v2/payment/checkout/create", { summary: "Create a cash checkout session", tag: "Payment", sec: "member", body: "CheckoutCreateRequest", ok: env(ref("CheckoutSessionOut")) }],
  ["post", "/api/v2/payment/create-payment-link", { summary: "Create payment link (legacy, NG/flutterwave)", tag: "Payment", sec: "member", body: "PaymentLink", ok: env(ref("CheckoutSessionOut")) }],
  ["post", "/api/v2/payment/pay-chapter", { summary: "Unlock a chapter with stars", tag: "Payment", sec: "member", body: "ChapterPayment", ok: env(ref("MessageOut")) }],
  ["post", "/api/v2/payment/subscribe-with-stars", { summary: "Subscribe using stars", tag: "Payment", sec: "member", body: "SubscriptionStarsPurchaseRequest", ok: env(ref("MessageOut")) }],
  ["post", "/api/v2/payment/webhooks/flutterwave", { summary: "Flutterwave webhook (raw body, verif-hash)", tag: "Payment", sec: "none", ok: env(ref("WebhookResultOut")) }],
  ["post", "/api/v2/payment/webhooks/paystack", { summary: "Paystack webhook (raw body, HMAC-SHA512)", tag: "Payment", sec: "none", ok: env(ref("WebhookResultOut")) }],
  ["post", "/api/v2/payment/webhooks/stripe", { summary: "Stripe webhook (raw body, signature)", tag: "Payment", sec: "none", ok: env(ref("WebhookResultOut")) }],
  ["post", "/api/v2/payment/webhook", { summary: "Legacy Flutterwave webhook alias", tag: "Payment", sec: "none", ok: env(ref("WebhookResultOut")) }],
];

const TAGS = [
  { name: "System", description: "Liveness." },
  { name: "User", description: "Auth, profile, Google OAuth, and member-facing reads." },
  { name: "Admin", description: "Admin auth (OTP-gated), management, and analytics." },
  { name: "Book", description: "Books (admin only)." },
  { name: "Chapter", description: "Chapters; access-gated for readers." },
  { name: "Page", description: "Pages; reading single pages tracks progress." },
  { name: "Bookmark", description: "Polymorphic bookmarks." },
  { name: "Like", description: "Chapter likes." },
  { name: "Comment", description: "Polymorphic, threaded comments." },
  { name: "AuthorRoom", description: "Author/chapter discussion rooms." },
  { name: "Reactions", description: "Reactions on author rooms." },
  { name: "Payment", description: "Bundles, checkout, stars wallet, and webhooks." },
];

export function buildOpenApiSpec(origin: string): Record<string, unknown> {
  const paths: Record<string, Record<string, Schema>> = {};
  for (const [method, path, opts] of ROUTES) {
    (paths[path] ??= {})[method] = operation(opts);
  }
  return {
    openapi: "3.0.3",
    info: {
      title: "MIE / Echoes Novel-App API (v2)",
      version: "2.0.0",
      description:
        "Next.js port of the v2 API. Every 2xx JSON response is wrapped in a success envelope " +
        "`{ success, message, data }`; errors use `{ success:false, message, data:null, errors? }`. " +
        "List endpoints return `{ items, meta, summary }`. Auth is a stateful Bearer JWT.",
    },
    servers: [{ url: origin || "/" }],
    tags: TAGS,
    paths,
    components: { securitySchemes, schemas },
  };
}
