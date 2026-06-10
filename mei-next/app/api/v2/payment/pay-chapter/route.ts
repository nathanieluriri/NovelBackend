export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyToken, getUserFromClaims } from "@/lib/http/guards";
import { payForChapterWithStars } from "@/lib/payments";

/** ChapterPayment — `{ bundle_id, chapterId }` (schema.md §5 / legacy). */
const ChapterPayment = z.object({
  bundle_id: z.string(),
  chapterId: z.string(),
});

/**
 * POST /api/v2/payment/pay-chapter — member.
 * Port of `make_payment_for_book` (inherited): stars-wallet chapter unlock.
 * Resolve the member user, then `payForChapterWithStars(user, bundle_id, chapterId)`.
 */
export const POST = withRoute(async (req) => {
  const claims = await verifyToken(req);
  const { bundle_id, chapterId } = await parseBody(req, ChapterPayment);
  const user = await getUserFromClaims(claims);
  return payForChapterWithStars(user, bundle_id, chapterId);
});
