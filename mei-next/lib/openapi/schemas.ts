/**
 * OpenAPI 3.0 component schemas for the v2 wire contract (see
 * ../../../nextjs-migration/schema.md). Hand-authored to mirror the serializers,
 * including the deliberate quirks (chapaterLabel, stopped_reading, +00:00 dates,
 * enum values on the wire). Plain data — consumed by lib/openapi/spec.ts.
 */

type Schema = Record<string, unknown>;

const str: Schema = { type: "string" };
const strN: Schema = { type: "string", nullable: true };
const int: Schema = { type: "integer" };
const intN: Schema = { type: "integer", nullable: true };
const num: Schema = { type: "number" };
const boolean: Schema = { type: "boolean" };
const dateStr: Schema = { type: "string", description: "ISO-8601 UTC (+00:00 offset)" };
const dateStrN: Schema = { type: "string", nullable: true, description: "ISO-8601 UTC (+00:00 offset)" };
const strArrN: Schema = { type: "array", items: { type: "string" }, nullable: true };

const arr = (items: Schema): Schema => ({ type: "array", items });
const obj = (properties: Record<string, Schema>, required?: string[]): Schema => ({
  type: "object",
  properties,
  ...(required && required.length ? { required } : {}),
});
const ref = (n: string): Schema => ({ $ref: `#/components/schemas/${n}` });
const enumStr = (...values: string[]): Schema => ({ type: "string", enum: values });
const enumStrN = (...values: string[]): Schema => ({ type: "string", enum: values, nullable: true });

const targetType: Schema = enumStr("book", "chapter", "page");
const accessType: Schema = enumStrN("free", "subscription", "paid");

export const securitySchemes: Record<string, Schema> = {
  bearerAuth: {
    type: "http",
    scheme: "bearer",
    bearerFormat: "JWT",
    description:
      "Stateful JWT. Send `Authorization: Bearer <accessToken>`. The token's inner id must resolve to a live accessToken row (< 10 days; admins must be activated).",
  },
};

export const schemas: Record<string, Schema> = {
  // -- envelopes / pagination ------------------------------------------------
  ErrorEnvelope: obj(
    {
      success: { type: "boolean", enum: [false] },
      message: str,
      data: { nullable: true },
      errors: { nullable: true, description: "Present only for structured errors (e.g. 422)." },
    },
    ["success", "message", "data"],
  ),
  ListMeta: obj(
    { skip: int, limit: int, returned: int, total: int, hasMore: boolean },
    ["skip", "limit", "returned", "total", "hasMore"],
  ),
  ListSummary: obj({ totalItems: int, returnedItems: int }, ["totalItems", "returnedItems"]),
  MessageOut: obj({ message: str }, ["message"]),
  DeletedOut: obj({ deleted: { type: "boolean", enum: [true] } }, ["deleted"]),
  HealthOut: obj({ status: enumStr("healthy") }, ["status"]),
  WebhookResultOut: obj({
    status: enumStr("fulfilled", "idempotent_replay"),
    txRef: strN,
    provider: strN,
  }),

  // -- summaries (embedded) --------------------------------------------------
  ChapterSummary: obj(
    {
      id: str,
      bookId: strN,
      chapterLabel: strN,
      number: intN,
      accessType,
      coverImage: strN,
      pageCount: intN,
      dateCreated: dateStrN,
      dateUpdated: dateStrN,
    },
    ["id"],
  ),
  PageSummary: obj(
    { id: str, chapterId: strN, status: strN, number: intN, textCount: intN, dateCreated: dateStrN, dateUpdated: dateStrN },
    ["id"],
  ),
  BookSummary: obj(
    { id: str, name: strN, number: intN, chapterCount: intN, dateCreated: dateStrN, dateUpdated: dateStrN },
    ["id"],
  ),

  // -- content ---------------------------------------------------------------
  BookOut: obj(
    {
      name: str,
      number: int,
      dateCreated: dateStrN,
      dateUpdated: dateStrN,
      chapterCount: intN,
      chapters: strArrN,
      id: strN,
      lastAccessed: dateStr,
    },
    ["name", "number"],
  ),
  ChapterOut: obj(
    {
      bookId: str,
      chapterLabel: strN,
      status: strN,
      accessType,
      unlockBundleId: strN,
      number: intN,
      id: strN,
      coverImage: strN,
      lastAccessed: dateStrN,
      dateCreated: dateStrN,
      dateUpdated: dateStrN,
      pageCount: intN,
      pages: strArrN,
      commentsCount: intN,
      likesCount: intN,
    },
    ["bookId"],
  ),
  ChapterOutSync: obj(
    { bookId: str, chapterLabel: strN, accessType, number: intN, id: strN, hasRead: boolean },
    ["bookId", "hasRead"],
  ),
  PageOut: obj(
    {
      chapterId: str,
      textContent: str,
      status: str,
      dateCreated: dateStrN,
      dateUpdated: dateStrN,
      textCount: intN,
      id: strN,
      lastAccessed: dateStrN,
    },
    ["chapterId", "textContent", "status"],
  ),

  // -- user ------------------------------------------------------------------
  Stage: obj({ currentStage: int, currentExperience: int }, ["currentStage", "currentExperience"]),
  SubscriptionInfo: obj({ active: boolean, expiresAt: strN }, ["active"]),
  ReadingHistory: obj({ chapterId: strN, chapterNumber: intN, chapterSnippet: strN }),
  UserOut: obj(
    {
      userId: strN,
      status: enumStrN("Active", "Inactive", "Suspended"),
      email: str,
      firstName: strN,
      lastName: strN,
      avatar: strN,
      accessToken: strN,
      refreshToken: strN,
      balance: intN,
      unlockedChapters: strArrN,
      dateCreated: dateStrN,
      stage: ref("Stage"),
      bookmarks: arr(ref("BookMarkOut")),
      likes: arr(ref("LikeOut")),
      stopped_reading: { ...ref("ReadingHistory"), nullable: true, description: "snake_case key (legacy quirk)" } as Schema,
      authProviders: arr(str),
      subscription: ref("SubscriptionInfo"),
    },
    ["email"],
  ),
  NewUserOut: obj(
    {
      userId: strN,
      email: str,
      balance: intN,
      accessToken: strN,
      refreshToken: strN,
      unlockedChapters: strArrN,
      firstName: strN,
      lastName: strN,
      avatar: strN,
      dateCreated: dateStrN,
      stage: ref("Stage"),
      bookmarks: arr(ref("BookMarkOut")),
      likes: arr(ref("LikeOut")),
      stopped_reading: { ...ref("ReadingHistory"), nullable: true } as Schema,
      authProviders: arr(str),
      subscription: ref("SubscriptionInfo"),
    },
    ["email"],
  ),
  OldUserOut: {
    allOf: [ref("NewUserOut")],
    description: "Like NewUserOut but accessToken and refreshToken are non-null.",
  },
  UserOutChapterDetails: {
    allOf: [ref("UserOut"), obj({ chapterDetails: arr(ref("ChapterOutSync")) })],
  },
  UserDetailsV2Out: obj(
    {
      userId: str,
      email: str,
      firstName: strN,
      lastName: strN,
      avatar: strN,
      summary: obj({ totalLikes: int, totalBookmarks: int }, ["totalLikes", "totalBookmarks"]),
      likes: arr(obj({ index: int, item: ref("LikeOut") }, ["index", "item"])),
      bookmarks: arr(obj({ index: int, item: ref("BookMarkOut") }, ["index", "item"])),
      readingProgress: { ...ref("ReadingProgressOut"), nullable: true } as Schema,
      likesMeta: ref("ListMeta"),
      bookmarksMeta: ref("ListMeta"),
    },
    ["userId", "email"],
  ),
  TokenRefreshOut: obj(
    { userId: str, dateCreated: dateStr, refreshToken: str, accessToken: str },
    ["userId", "refreshToken", "accessToken"],
  ),

  // -- interactions ----------------------------------------------------------
  CommentOut: obj(
    {
      id: strN,
      userId: str,
      role: str,
      text: str,
      targetType,
      targetId: str,
      parentCommentId: strN,
      commentType: enumStrN("reply_target", "Reply To Chapter", "Reply To Comment", "Reply To Reply"),
      dateCreated: dateStrN,
      firstName: strN,
      lastName: strN,
      avatar: strN,
      email: strN,
    },
    ["userId", "role", "text", "targetType", "targetId"],
  ),
  LikeOut: obj(
    {
      chapterId: str,
      userId: str,
      role: str,
      likeType: enumStrN("Liked Chapter", "Liked Comment", "Liked Comment Reply", "Liked Reply To Reply"),
      chapaterLabel: { type: "string", description: "Misspelled on purpose (legacy wire field)." },
      dateCreated: dateStrN,
      id: strN,
      chapterSummary: { ...ref("ChapterSummary"), nullable: true } as Schema,
    },
    ["chapterId", "userId", "role", "chapaterLabel"],
  ),
  LikeWithUserOut: {
    allOf: [
      ref("LikeOut"),
      obj({ user: { ...obj({ firstName: strN, lastName: strN, avatar: strN, email: strN }), nullable: true } as Schema }),
    ],
  },
  BookMarkOut: obj(
    {
      userId: str,
      targetType,
      targetId: str,
      chapterLabel: strN,
      chapterId: strN,
      pageId: strN,
      dateCreated: dateStrN,
      id: strN,
      pageNumber: intN,
      chapterSummary: { ...ref("ChapterSummary"), nullable: true } as Schema,
    },
    ["userId", "targetType", "targetId"],
  ),
  ReactionOut: obj(
    { reaction: str, authorRoomId: str, id: strN, dateCreated: dateStrN, lastUpdated: dateStrN },
    ["reaction", "authorRoomId"],
  ),
  AuthorRoomOut: obj(
    {
      text: str,
      chapterId: str,
      id: strN,
      dateCreated: dateStrN,
      lastUpdated: dateStrN,
      chapterSummary: { ...ref("ChapterSummary"), nullable: true } as Schema,
      reactionSummary: { type: "object", additionalProperties: { type: "integer" } },
      userReaction: strN,
    },
    ["text", "chapterId"],
  ),
  ReadingProgressOut: obj(
    {
      userId: str,
      chapterId: str,
      pageId: str,
      dateUpdated: strN,
      chapterSummary: { ...ref("ChapterSummary"), nullable: true } as Schema,
      pageSummary: { ...ref("PageSummary"), nullable: true } as Schema,
    },
    ["userId", "chapterId", "pageId"],
  ),
  EntitlementOut: obj(
    { userId: str, chapterId: str, grantType: enumStr("chapter_unlock"), source: strN, txRef: strN, id: strN, createdAt: dateStrN },
    ["userId", "chapterId"],
  ),

  // -- payments --------------------------------------------------------------
  CheckoutSessionOut: obj(
    {
      checkoutUrl: str,
      provider: enumStr("flutterwave", "paystack", "stripe"),
      providerReference: str,
      txRef: str,
      status: enumStr("initiated", "pending", "verified", "fulfilled", "failed"),
      expiresAt: strN,
    },
    ["checkoutUrl", "provider", "providerReference", "txRef", "status"],
  ),
  PaymentBundlesOut: obj(
    {
      id: str,
      amount: intN,
      numberOfstars: intN,
      bundleType: enumStrN(
        "cash",
        "purchaseOfBooks",
        "transferringStarsToOtherUsers",
        "cashPromo",
        "bookPromo",
        "subscription",
        "subscriptionCash",
        "subscriptionStars",
      ),
      durationDays: intN,
      description: str,
      features: arr(str),
      dateCreated: dateStrN,
    },
    ["id", "description", "features"],
  ),
  PricingBundleOut: obj(
    { id: str, bundleType: str, description: str, features: arr(str), durationDays: intN, cashAmount: intN, starAmount: intN, dateCreated: dateStrN },
    ["id", "bundleType", "description", "features"],
  ),
  PricingCatalogOut: obj(
    {
      subscriptionPlans: arr(ref("PricingBundleOut")),
      starBundles: arr(ref("PricingBundleOut")),
      chapterUnlockBundles: arr(ref("PricingBundleOut")),
    },
    ["subscriptionPlans", "starBundles", "chapterUnlockBundles"],
  ),

  // -- admin -----------------------------------------------------------------
  NewAdminOut: obj(
    {
      email: str,
      invitedBy: strN,
      userId: strN,
      accessToken: strN,
      refreshToken: strN,
      firstName: strN,
      lastName: strN,
      avatar: strN,
      dateCreated: dateStrN,
    },
    ["email"],
  ),
  ChapterInteractionUserOut: obj(
    { userId: str, firstName: strN, lastName: strN, email: strN, avatar: strN, interactionCount: int, lastInteractionAt: strN },
    ["userId"],
  ),
  AnalyticsMetric: obj({ total: strN, change: strN, changeType: enumStrN("increase", "decrease", "no change") }),
  AdminDashboardAnalytics: obj({
    chapterAnalytics: ref("AnalyticsMetric"),
    pageAnalytics: ref("AnalyticsMetric"),
    readerAnalytics: ref("AnalyticsMetric"),
    revenueAnalytics: ref("AnalyticsMetric"),
    recentChapters: arr(ref("ChapterOut")),
    recentUsers: arr(ref("UserOut")),
  }),

  // -- request bodies --------------------------------------------------------
  NewUserBase: obj(
    {
      provider: enumStr("credentials", "google"),
      email: { type: "string", format: "email" },
      password: strN,
      googleAccessToken: strN,
      firstName: strN,
      lastName: strN,
      avatar: strN,
    },
    ["provider", "email"],
  ),
  OldUserBase: obj(
    { email: { type: "string", format: "email" }, password: str, provider: enumStr("credentials", "google") },
    ["email", "password"],
  ),
  RefreshTokenRequest: obj({ refreshToken: str }, ["refreshToken"]),
  UserUpdate: obj({ firstName: strN, lastName: strN, avatar: strN, status: enumStrN("Active", "Inactive", "Suspended") }),
  EmailBody: obj({ email: { type: "string", format: "email" } }, ["email"]),
  ConcludePasswordBody: obj({ email: { type: "string", format: "email" }, otp: str, password: str }, ["email", "otp", "password"]),
  GoogleExchangeRequest: obj({ code: str }, ["code"]),
  NewAdminCreate: obj(
    { email: { type: "string", format: "email" }, password: str, firstName: strN, lastName: strN, avatar: strN },
    ["email", "password"],
  ),
  AdminBase: obj({ email: { type: "string", format: "email" }, password: str }, ["email", "password"]),
  AdminUpdate: obj({ firstName: strN, lastName: strN, avatar: strN }),
  VerificationRequest: obj({ access_token: str, otp: str }, ["access_token", "otp"]),
  InviteBody: obj({ email: { type: "string", format: "email" } }, ["email"]),
  BookBaseRequest: obj({ name: str }, ["name"]),
  BookUpdate: obj({ name: strN, number: intN, chapterCount: intN, chapters: strArrN }),
  ChapterBaseRequest: obj(
    { bookId: str, chapterLabel: str, status: strN, accessType, unlockBundleId: strN, coverImage: strN },
    ["bookId", "chapterLabel"],
  ),
  ChapterUpdateRequest: obj({ chapterLabel: strN, status: strN, accessType, unlockBundleId: strN, coverImage: strN }),
  PageBase: obj({ chapterId: str, textContent: str, status: str }, ["chapterId", "textContent", "status"]),
  PageUpdateRequest: obj({ textContent: str, status: strN }, ["textContent"]),
  BookMarkCreateRequest: obj({ targetType, targetId: strN, pageId: strN }),
  LikeBaseRequest: obj({ chapterId: str }, ["chapterId"]),
  CommentCreateRequest: obj(
    {
      text: str,
      targetType,
      targetId: strN,
      chapterId: strN,
      parentCommentId: strN,
      commentType: enumStrN("reply_target", "Reply To Chapter", "Reply To Comment", "Reply To Reply"),
    },
    ["text"],
  ),
  UpdateCommentBaseRequest: obj({ commentId: str, text: str }, ["commentId", "text"]),
  AuthorRoomBase: obj({ text: str, chapterId: str }, ["text", "chapterId"]),
  AuthorRoomUpdate: obj({ text: str }, ["text"]),
  ReactionBase: obj({ reaction: str, authorRoomId: str, userId: str }, ["reaction", "authorRoomId", "userId"]),
  ReactionUpdate: obj({ reaction: strN }),
  CheckoutCreateRequest: obj(
    {
      bundleId: str,
      countryCode: { type: "string", minLength: 2, maxLength: 2 },
      provider: enumStrN("flutterwave", "paystack", "stripe"),
      chapterId: strN,
      successUrl: strN,
      cancelUrl: strN,
    },
    ["bundleId", "countryCode"],
  ),
  SubscriptionStarsPurchaseRequest: obj({ bundleId: str }, ["bundleId"]),
  ChapterPayment: obj({ bundleId: str }, ["bundleId"]),
  PaymentLink: obj({ bundleId: str, chapterId: strN }, ["bundleId"]),
  PaymentBundles: obj(
    {
      bundleType: enumStr(
        "cash",
        "purchaseOfBooks",
        "transferringStarsToOtherUsers",
        "cashPromo",
        "bookPromo",
        "subscription",
        "subscriptionCash",
        "subscriptionStars",
      ),
      amount: intN,
      numberOfstars: intN,
      durationDays: intN,
      description: str,
      features: arr(str),
    },
    ["bundleType", "description"],
  ),
  PaymentBundlesUpdate: obj({ amount: intN, numberOfstars: intN, durationDays: intN, description: strN, features: arr(str) }),
};
