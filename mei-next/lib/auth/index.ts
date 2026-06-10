/**
 * Auth barrel — pinned seam (CONVENTIONS.md "@/lib/auth").
 * Other slices import everything auth-related from here.
 */

// jwt
export {
  signMemberJwt,
  signAdminJwt,
  decodeJwt,
  decodeJwtIgnoreExpiry,
  type Claims,
} from "./jwt";

// token lifecycle
export {
  issueMemberTokens,
  issueAdminTokens,
  refreshTokens,
  revokeAllTokensForUser,
  activateAdminToken,
  validateMemberAccessToken,
  validateAdminAccessToken,
  getAccessTokenRow,
  extractBearerToken,
} from "./tokens";

// otp (Redis, 380s, 6 distinct digits)
export {
  generateOtp,
  storeUserOtp,
  verifyUserOtp,
  storeAdminLoginOtp,
  verifyAdminLoginOtp,
} from "./otp";

// google oauth
export { buildGoogleAuthRedirect, handleGoogleCallback, exchangeGoogleCode } from "./oauth";

// password hashing (bcrypt cost 12)
export { hashPassword, checkPassword } from "./hash";
