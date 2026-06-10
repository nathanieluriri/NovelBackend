# CONVENTIONS.md — Build Conventions & Pinned Seams

Read this FIRST. You are implementing one slice of this Next.js backend; other agents implement the
rest in parallel. This file pins the shared interfaces ("seams") so everything composes. The planning
docs live at `../../../nextjs-migration/` (schema.md, endpoints.md, auth.md, payments.md, caching.md,
reading-progress.md, email-resend.md, data-models.md). The legacy FastAPI code (behavioral authority)
is at `../` (repo root: `api/`, `services/`, `repositories/`, `schemas/`, `security/`, `core/`).

## Hard rules
1. **Only create/modify files you own** (your prompt lists them). Importing anything is fine.
2. **TypeScript strict** — must compile under `tsc --noEmit`. No `any` unless unavoidable.
3. **No top-level side effects** that need env/network (no `new Stripe(...)` or `Redis.fromEnv()` at
   module scope — wrap in lazy functions). Mongoose schema/model registration at module scope is fine.
4. **Never run** npm install / build / git commands.
5. Every route file starts with:
   ```ts
   export const runtime = "nodejs";
   export const dynamic = "force-dynamic";
   ```
6. Next.js 15+ App Router: `params` is a **Promise** — `const { id } = await ctx.params;`.
7. Query params: `new URL(req.url).searchParams`.
8. Wire contract quirks are sacred (schema.md §0): `chapaterLabel` (sic), `stopped_reading`
   (snake_case), `TransactionType` (PascalCase), `+00:00` dates via `toIsoOffset`, enum values on the
   wire, envelope key order.
9. Call `await db()` at the top of any function that touches Mongo.
10. Errors: `throw new HttpError(status, message)` — never return error Responses manually from
    handlers (withRoute converts).

## Foundation (already written — import, don't recreate)
```ts
import { db } from "@/lib/db";
import { redis, rGet, rSetEx, rDel } from "@/lib/redis";              // best-effort helpers
import { env, requireEnv, envBool, envInt } from "@/lib/env";
import { HttpError } from "@/lib/http/errors";
import { withRoute } from "@/lib/http/route";
import { success, successBody, errorResponse, paginate, paginateIndexed,
         parseSkipLimit, clampLimit, buildListMeta } from "@/lib/http/envelope";
import { parseBody, require24, zodToPydanticErrors } from "@/lib/http/validate";
import { toIsoOffset, nowIso, nowEpoch, isOlderThanDays } from "@/lib/util/dates";
```

Route handler pattern:
```ts
export const GET = withRoute(async (req, ctx) => {
  const { chapterId } = await ctx.params;
  require24(chapterId, "chapterId");
  const claims = await verifyAnyToken(req);
  const { skip, limit } = parseSkipLimit(req);
  await db();
  // ... service call ...
  return paginate(items, skip, limit, total);   // withRoute envelopes it
});
// POST with 201: export const POST = withRoute(async (req) => {...}, { status: 201 });
// Redirects (OAuth): return Response.redirect(url, 302) — withRoute passes Responses through raw.
```

## Pinned seams (exact export names/signatures — implement OR consume per your prompt)

### `@/lib/models` (models agent) — re-exports every model
`User, Admin, AllowedAdmin, Book, Chapter, Page, Like, Bookmark, Comment, Reaction, AuthorRoom,
ReadingProgress, ReadRecord, Entitlement, PaymentBundle, PaymentRuntime, WebhookEvent, Transaction,
AccessToken, RefreshToken, GoogleOAuthExchange, LoginAttempt`
All Mongoose models bound to the exact legacy collection names (data-models.md). FK fields are
`String`. Each model exported individually AND from `lib/models/index.ts`.

### `@/lib/serializers` (serializers agent) — pure doc→wire mappers
```ts
toBookOut(doc): BookOut
toChapterOut(doc, extras?: {pageCount?, pages?, commentsCount?, likesCount?}): ChapterOut
toChapterSyncVersion(doc, hasRead: boolean)
toPageOut(doc): PageOut
toUserOut(doc, extras?), toNewUserOut(doc, extras?), toOldUserOut(doc, extras)   // extras: {accessToken, refreshToken, bookmarks, likes, stopped_reading, chapterDetails}
toCommentOut(doc, user?: {firstName,lastName,avatar,email})
toLikeOut(doc, chapterSummary?), toLikeWithUserOut(doc, user, chapterSummary?)
toBookmarkOut(doc, extras?: {pageNumber?, chapterSummary?})
toReactionOut(doc)            // date_created→dateCreated, last_updated→lastUpdated (epoch→ISO)
toAuthorRoomOut(doc, extras?: {chapterSummary?, reactionSummary?, userReaction?})
toReadingProgressOut(doc, extras?: {chapterSummary?, pageSummary?})
toEntitlementOut(doc)
toPaymentBundlesOut(doc), toPricingBundleOut(doc), toTransactionOut(doc)
toNewAdminOut(doc, extras?: {accessToken?, refreshToken?})
toChapterSummary(doc), toPageSummary(doc), toBookSummary(doc)
toChapterInteractionUserOut(user, interactionCount, lastInteractionAt)
```
Serializers are sync + pure (no DB). They take plain docs (`.lean()` results) and produce the EXACT
wire shapes from schema.md §4 including `id: String(_id)`, `lastAccessed: nowIso()` where specified,
defaults, and quirks.

### `@/lib/cache/summary` (cache agent)
```ts
getBookSummary(id: string): Promise<BookSummary | null>
getChapterSummary(id: string): Promise<ChapterSummary | null>
getPageSummary(id: string): Promise<PageSummary | null>
invalidateSummaries(ids: { books?: string[]; chapters?: string[]; pages?: string[] }): Promise<void>
```
Key `summary:{type}:{id}:v1`, TTL 900, best-effort, cache-aside per caching.md. Returns null when the
entity does not exist.

### `@/lib/email` (email agent)
```ts
sendAdminOtp(a: { to: string; otp: string }): Promise<void>
sendAdminInvitation(a: { to: string; firstName: string; lastName: string; inviterEmail: string }): Promise<void>
sendNewIpWarning(a: { to: string; firstName: string; lastName: string; timeData: string; ip: string; location: string; extraData: string }): Promise<void>
sendPasswordResetOtp(a: { to: string; otp: string }): Promise<void>
```
All best-effort (never throw). Resend per email-resend.md.

### `@/lib/auth` (auth agent) — barrel `lib/auth/index.ts`
```ts
// jwt
signMemberJwt(innerId: string): Promise<string>
signAdminJwt(innerId: string): Promise<string>
decodeJwt(token: string): Promise<Claims | null>            // null on invalid/expired
decodeJwtIgnoreExpiry(token: string): Promise<Claims | null>
type Claims = { accessToken: string; role: "member" | "admin"; exp: number }
// token lifecycle
issueMemberTokens(userId: string): Promise<{ accessToken: string; refreshToken: string }>
issueAdminTokens(userId: string): Promise<{ accessToken: string; refreshToken: string }>  // row status:"inactive"
refreshTokens(req: Request, refreshToken: string): Promise<{ userId: string; dateCreated: string; refreshToken: string; accessToken: string }>
revokeAllTokensForUser(userId: string): Promise<void>
activateAdminToken(innerId: string): Promise<void>
// otp (Redis, 380s, 6 distinct digits)
generateOtp(): string
storeUserOtp(email: string, otp: string): Promise<void>          // key=otp, value=email
verifyUserOtp(email: string, otp: string): Promise<boolean>
storeAdminLoginOtp(adminJwt: string, otp: string): Promise<void> // key=jwt, value=otp
verifyAdminLoginOtp(adminJwt: string, otp: string): Promise<boolean>
// google oauth
buildGoogleAuthRedirect(target?: string, redirectPath?: string): Promise<Response>
handleGoogleCallback(req: Request): Promise<Response>            // 302 to FE success/error
exchangeGoogleCode(code: string): Promise<{ userId: string }>    // atomic single-use consume
```

### `@/lib/http/guards` (auth agent)
```ts
verifyToken(req: Request): Promise<Claims>          // member; 401 otherwise
verifyAdminToken(req: Request): Promise<Claims>     // admin active; 401 variants per auth.md
verifyAnyToken(req: Request): Promise<Claims>
resolveReader(claims: Claims): Promise<{ role: "member" | "admin"; user: UserDoc | null }>
getUserFromClaims(claims: Claims): Promise<UserDoc> // loads session row → user; 401 if gone
```

### `@/lib/services/access` (payments agent)
```ts
isSubscriptionActive(sub?: { active?: boolean; expiresAt?: string | null }): boolean
isChapterUnlocked(user: UserDoc, chapterId: string): Promise<boolean>
hasChapterAccess(user: UserDoc, chapter: ChapterDoc): Promise<boolean>
```

### `@/lib/payments` (payments agent) — barrel `lib/payments/index.ts`
```ts
createCheckout(user: UserDoc, body: CheckoutCreateRequest): Promise<CheckoutSessionOut>
processWebhook(provider: "flutterwave" | "paystack" | "stripe", rawBody: string, headers: Record<string, string>): Promise<unknown>
getPricingCatalog(): Promise<PricingCatalogOut>
payForChapterWithStars(user: UserDoc, bundleId: string): Promise<unknown>
purchaseSubscriptionWithStars(user: UserDoc, bundleId: string): Promise<unknown>
recordSubscriptionPurchase(userId: string, bundle: BundleDoc, txRef: string): Promise<unknown>
```

### `@/lib/services/readingProgress` (page agent)
```ts
trackReadingProgress(userId?: string, chapterId?: string, pageId?: string): Promise<void>  // guarded idempotent upsert
getUserReadingProgress(userId: string): Promise<ReadingProgressOut>  // throws HttpError 404/403 per reading-progress.md
```

### Loose typing at seams
Use `type UserDoc = Record<string, any>` style loose doc types at seams (legacy data is heterogeneous);
keep strong types for wire shapes inside serializers.

## Behavior reminders
- Auth is STATEFUL: JWT → inner ObjectId → `accessToken` row must exist, <10 days, admins `active`.
- bcrypt cost 12 (`bcryptjs`); jose for JWT (HS256, random `kid` from the `secret_keys` doc, header `kid`).
- Cache bust on book/chapter/page mutations per the table in caching.md (bust parents).
- Page single-GET: reading-progress upsert via `after()` from `next/server`, members only.
- Webhooks: read RAW body (`await req.text()`), verify signature, idempotency insert first.
- Pagination: flat items; ONLY user-v2 likes/bookmarks use `paginateIndexed`.
- 404 "already deleted" semantics on remove endpoints; 403 for cross-user bookmark listing; 409 duplicate reaction.
