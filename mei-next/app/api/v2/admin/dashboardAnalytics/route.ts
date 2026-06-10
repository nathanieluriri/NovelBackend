export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { performAnalytics } from "@/lib/services/dashboardAnalytics";

/**
 * GET /api/v2/admin/dashboardAnalytics  (admin)
 * Returns AdminDashboardAnalytics: today-vs-yesterday count deltas for
 * chapters/pages/users, HARDCODED revenue (legacy parity), the 8 most-recently-
 * updated chapters with page/word counts, and the 8 newest users.
 */
export const GET = withRoute(async (req) => {
  await verifyAdminToken(req);
  return performAnalytics();
});
