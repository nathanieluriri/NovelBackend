export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyToken, getUserFromClaims } from "@/lib/http/guards";
import { purchaseSubscriptionWithStars } from "@/lib/payments";

/**
 * SubscriptionStarsPurchaseRequest — schema.md §5. Accepts `bundleId` OR the
 * `bundle_id` alias (legacy `AliasChoices`), serializing to `bundleId`; the value
 * must be exactly 24 chars (legacy model-validator → 422).
 */
const SubscriptionStarsPurchaseRequest = z
  .object({
    bundleId: z.string().optional(),
    bundle_id: z.string().optional(),
  })
  .transform((v, ctx) => {
    const bundleId = v.bundleId ?? v.bundle_id;
    if (bundleId === undefined) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Field required", path: ["bundleId"] });
      return z.NEVER;
    }
    if (bundleId.length !== 24) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "bundleId must be exactly 24 characters long",
        path: ["bundleId"],
      });
      return z.NEVER;
    }
    return { bundleId };
  });

/**
 * POST /api/v2/payment/subscribe-with-stars — member.
 * Port of `subscribe_with_stars` (inherited): stars-wallet subscription purchase.
 * Resolve the member user, then `purchaseSubscriptionWithStars(user, bundleId)`.
 */
export const POST = withRoute(async (req) => {
  const claims = await verifyToken(req);
  const { bundleId } = await parseBody(req, SubscriptionStarsPurchaseRequest);
  const user = await getUserFromClaims(claims);
  return purchaseSubscriptionWithStars(user, bundleId);
});
