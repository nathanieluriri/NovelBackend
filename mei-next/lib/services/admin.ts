/**
 * Admin service — port of `services/admin_services.py`,
 * `security/admin_otp.py` (`send_otp`/`generate_otp`/`verify_otp` flows) and the
 * geo/IP enrichment in `services/email_service.py` (`get_location`) +
 * `repositories/admin_repo.py` (`get_location_details_for_admin`).
 *
 * Drives the `/api/v2/admin/*` routes (sign-up, sign-in, verify, invite,
 * change-password, details, all/details, update).
 *
 * Token lifecycle (issueAdminTokens → inactive row), JWT signing, OTP storage,
 * password hashing and email sending all go through the pinned seams.
 */
import { db } from "@/lib/db";
import { redis } from "@/lib/redis";
import { HttpError } from "@/lib/http/errors";
import { Admin, AllowedAdmin, LoginAttempt, type AdminDoc } from "@/lib/models";
import {
  issueAdminTokens,
  storeAdminLoginOtp,
  generateOtp,
  verifyAdminLoginOtp,
  activateAdminToken,
  revokeAllTokensForUser,
  decodeJwt,
  getAccessTokenRow,
  hashPassword,
  checkPassword,
  storeUserOtp,
  verifyUserOtp,
} from "@/lib/auth";
import {
  sendAdminOtp,
  sendAdminInvitation,
  sendNewIpWarning,
  sendPasswordResetOtp,
} from "@/lib/email";
import { toNewAdminOut, type NewAdminOut } from "@/lib/serializers/admin";
import { env } from "@/lib/env";
import { nowIso } from "@/lib/util/dates";

/* ------------------------------------------------------------------ *
 * Geo / IP enrichment (best-effort) — port of email_service.get_location
 * + admin_repo.get_location_details_for_admin (LoginAttempts consume).
 * ------------------------------------------------------------------ */

interface LocationData {
  ip: string;
  city: string | null;
  region: string | null;
  country: string | null;
  latitude: string;
  longitude: string;
  Network: string | null; // ⚠ capital N — legacy field name
  timezone: string | null;
  dateTime: string;
  clientType: string;
  userId: string;
}

/** Best-effort client IP from forwarding headers (serverless). */
function clientIpFromRequest(req: Request): string {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) {
    const first = xff.split(",")[0]?.trim();
    if (first) return first;
  }
  return req.headers.get("x-real-ip")?.trim() || "unknown";
}

/**
 * Port of `get_location`: enriches the request IP via ipinfo.io (token
 * `LOCATION_API`). Best-effort — if the token is missing or the lookup fails we
 * still return a minimally-populated ClientData (legacy raised on lookup error;
 * we degrade so the auth response is never blocked by geo).
 */
async function getLocation(req: Request, clientType: string, userId: string): Promise<LocationData> {
  const ip = clientIpFromRequest(req);
  const base: LocationData = {
    ip,
    city: null,
    region: null,
    country: null,
    latitude: "None",
    longitude: "None",
    Network: null,
    timezone: null,
    dateTime: nowIso(),
    clientType,
    userId,
  };

  const token = env("LOCATION_API");
  if (!token || ip === "unknown") return base;

  try {
    const res = await fetch(`https://ipinfo.io/${ip}/json/?token=${token}`);
    if (!res.ok) return base;
    const data = (await res.json()) as Record<string, unknown>;
    const loc = data.loc === null || data.loc === undefined ? "None" : String(data.loc);
    return {
      ...base,
      city: data.city === undefined || data.city === null ? null : String(data.city),
      region: data.region === undefined || data.region === null ? null : String(data.region),
      country: data.country === undefined || data.country === null ? null : String(data.country),
      latitude: loc,
      longitude: loc,
      Network: data.org === undefined || data.org === null ? null : String(data.org),
      timezone: data.timezone === undefined || data.timezone === null ? null : String(data.timezone),
    };
  } catch {
    return base;
  }
}

/**
 * Port of `get_location_details_for_admin`: atomically consume (find-one-and-
 * delete) the previous LoginAttempts row for this admin so the *next* login can
 * compare IPs. Best-effort.
 */
async function consumePreviousLoginAttempt(userId: string): Promise<LocationData | null> {
  try {
    const doc = await LoginAttempt.findOneAndDelete({ userId }).lean<Record<string, unknown>>();
    return (doc as LocationData | null) ?? null;
  } catch {
    return null;
  }
}

/** Persist the current attempt (legacy `create_email_log` after the OTP send). */
async function saveLoginAttempt(location: LocationData): Promise<void> {
  try {
    await LoginAttempt.create(location);
  } catch {
    /* best-effort */
  }
}

/** Human-readable timestamp like legacy `"%A, %B %d, %Y at %I:%M %p"`. */
function formatNow(): string {
  // Locale-stable English long format (legacy used the server locale; en-US is
  // the practical equivalent for the security email's display).
  return new Date().toLocaleString("en-US", {
    weekday: "long",
    month: "long",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * Port of `send_otp`: consume the prior LoginAttempts row; if it exists and the
 * IP is unchanged, just email the OTP. Otherwise (IP changed OR first login),
 * also email the new-IP security warning. Finally persist the current attempt.
 * All sends are best-effort. Mirrors the legacy ordering exactly.
 */
async function sendAdminLoginOtpWithIpCheck(args: {
  otp: string;
  location: LocationData;
  adminEmail: string;
  firstName: string;
  lastName: string;
}): Promise<void> {
  const { otp, location, adminEmail, firstName, lastName } = args;
  const previous = await consumePreviousLoginAttempt(location.userId);

  const sameIp = previous !== null && previous.ip === location.ip;
  if (!sameIp) {
    // IP changed OR first login → warning first, then OTP (legacy order).
    await sendNewIpWarning({
      to: adminEmail,
      firstName,
      lastName,
      timeData: formatNow(),
      ip: location.ip,
      location: `${location.city}, ${location.region}, ${location.country} `,
      extraData: `Network-${location.Network}, Longitude: ${location.longitude}, Latitude: ${location.latitude}`,
    });
  }
  await sendAdminOtp({ to: adminEmail, otp });
  await saveLoginAttempt(location);
}

/* ------------------------------------------------------------------ *
 * Allowlist
 * ------------------------------------------------------------------ */

/** Legacy `get_allowd_admin_emails`: AllowedAdmins membership gate. */
async function isAllowedAdminEmail(email: string): Promise<boolean> {
  const allowed = await AllowedAdmin.findOne({ email }).lean();
  return allowed !== null;
}

/* ------------------------------------------------------------------ *
 * Registration / login
 * ------------------------------------------------------------------ */

export interface NewAdminCreateInput {
  email: string;
  password: string;
  firstName: string | null;
  lastName: string | null;
  avatar: string | null;
}

export interface AdminBaseInput {
  email: string;
  password: string;
}

/**
 * Port of `register_admin_func`: allowlist-gated; 409 if the admin already
 * exists; bcrypt the password; create the admin; issue ADMIN tokens (the access
 * row is created `status:"inactive"`); store + email the login OTP (+ IP-change
 * warning per legacy); return NewAdminOut with the inactive tokens.
 */
export async function registerAdmin(req: Request, input: NewAdminCreateInput): Promise<NewAdminOut> {
  await db();

  if (!(await isAllowedAdminEmail(input.email))) {
    throw new HttpError(400, "This Email isn't Allowed To Register As An Admin");
  }

  const existing = await Admin.findOne({ email: input.email }).lean<AdminDoc>();
  if (existing) {
    throw new HttpError(409, "User already exists");
  }

  const hashed = await hashPassword(input.password);
  const created = await Admin.create({
    email: input.email,
    password: hashed,
    firstName: input.firstName,
    lastName: input.lastName,
    avatar: input.avatar,
    dateCreated: nowIso(),
  });
  const adminDoc = created.toObject() as AdminDoc;
  const userId = String(adminDoc._id);

  const { accessToken, refreshToken } = await issueAdminTokens(userId);

  const otp = generateOtp();
  await storeAdminLoginOtp(accessToken, otp);

  const location = await getLocation(req, "admin", userId);
  await sendAdminLoginOtpWithIpCheck({
    otp,
    location,
    adminEmail: input.email,
    firstName: String(adminDoc.firstName ?? ""),
    lastName: String(adminDoc.lastName ?? ""),
  });

  return toNewAdminOut(adminDoc, { accessToken, refreshToken });
}

/**
 * Port of `login_admin_func`: lookup admin by email; 404 if missing; 422 if no
 * password stored; 401 on bad password; else issue inactive admin tokens, store
 * + email the login OTP (+ IP warning), return NewAdminOut.
 */
export async function loginAdmin(req: Request, input: AdminBaseInput): Promise<NewAdminOut> {
  await db();

  const existing = await Admin.findOne({ email: input.email }).lean<AdminDoc>();
  if (!existing) {
    throw new HttpError(404, "User Not Found");
  }

  const stored = existing.password;
  if (stored === null || stored === undefined) {
    throw new HttpError(422, "Password wasn't provided");
  }

  const ok = await checkPassword(input.password, stored);
  if (!ok) {
    throw new HttpError(401, "Password Incorrect");
  }

  const userId = String(existing._id);
  const { accessToken, refreshToken } = await issueAdminTokens(userId);

  const otp = generateOtp();
  await storeAdminLoginOtp(accessToken, otp);

  const location = await getLocation(req, "admin", userId);
  await sendAdminLoginOtpWithIpCheck({
    otp,
    location,
    adminEmail: input.email,
    firstName: String(existing.firstName ?? ""),
    lastName: String(existing.lastName ?? ""),
  });

  return toNewAdminOut(existing, { accessToken, refreshToken });
}

/* ------------------------------------------------------------------ *
 * OTP verification (activate the admin access token)
 * ------------------------------------------------------------------ */

/**
 * Port of `verify_otp` (security/admin_otp.py): the two failure modes are
 * DISTINCT on the wire and must not collapse:
 *  - key absent (OTP expired / wrong access_token) → 401 "Invalid Access Token"
 *  - key present but value != otp                  → 401 "Incorrect OTP"
 *  - match → delete key, decode the JWT, flip the admin access row to
 *    `status:"active"`, return true.
 *  - undecodable JWT after a matching OTP → 401 "Invalid Access Token (token expired)"
 *
 * Legacy reads `exists(accessToken)` first to separate the two, so we probe the
 * key directly (key = adminJWT, value = otp — the reversed admin-login layout)
 * before delegating the compare-and-delete to verifyAdminLoginOtp.
 */
export async function verifyAdminOtp(accessToken: string, otp: string): Promise<boolean> {
  await db();
  const stored = await redis().get<unknown>(accessToken);
  if (stored === null || stored === undefined) {
    throw new HttpError(401, "Invalid Access Token");
  }
  const valid = await verifyAdminLoginOtp(accessToken, otp);
  if (!valid) {
    throw new HttpError(401, "Incorrect OTP");
  }
  const claims = await decodeJwt(accessToken);
  if (!claims) {
    throw new HttpError(401, "Invalid Access Token (token expired)");
  }
  await activateAdminToken(claims.accessToken);
  return true;
}

/* ------------------------------------------------------------------ *
 * Invitation
 * ------------------------------------------------------------------ */

/**
 * Port of `invitation_process` + `send_invitation`: resolve the inviter admin
 * from the (active) admin access token; when the inviter's firstName is NOT
 * "Default", write an AllowedAdmin row (`{email, invitedBy, dateCreated}`);
 * then email the invitation. Best-effort email.
 */
export async function processInvitation(inviterAccessTokenInnerId: string, invitedEmail: string): Promise<void> {
  await db();
  const inviter = await resolveAdminByInnerToken(inviterAccessTokenInnerId);
  if (!inviter) {
    throw new HttpError(404, "Details not found");
  }

  const firstName = String(inviter.firstName ?? "");
  const lastName = String(inviter.lastName ?? "");
  const inviterEmail = String(inviter.email ?? "");

  if (firstName !== "Default") {
    try {
      await AllowedAdmin.create({
        email: invitedEmail,
        invitedBy: inviterEmail,
        dateCreated: nowIso(),
      });
    } catch {
      // Unique index collision (already invited) — legacy let the email proceed.
    }
  }

  await sendAdminInvitation({
    to: invitedEmail,
    firstName,
    lastName,
    inviterEmail,
  });
}

/* ------------------------------------------------------------------ *
 * Password reset (mirrors the user flow)
 * ------------------------------------------------------------------ */

/** Port of `change_of_admin_password_flow1`: 404 if no admin; else email OTP. */
export async function initiateAdminPasswordChange(email: string): Promise<void> {
  await db();
  const admin = await Admin.findOne({ email }).lean<AdminDoc>();
  if (!admin) {
    throw new HttpError(404, "Admin Doesn't exist");
  }
  // Admin password-reset OTP layout: key = otp, value = email (legacy
  // generate_otp_admin_password). Reuse the shared user-OTP store helper.
  const otp = generateOtp();
  await storeUserOtp(email, otp);
  await sendPasswordResetOtp({ to: email, otp });
}

/**
 * Port of `change_of_admin_password_flow2`: verify OTP (key=otp, value=email);
 * on success bcrypt the new password, replace it, and revoke all tokens (logout
 * everywhere). Returns true/false matching the legacy message contract.
 */
export async function concludeAdminPasswordChange(
  email: string,
  otp: string,
  password: string,
): Promise<boolean> {
  await db();
  const valid = await verifyUserOtp(email, otp);
  if (!valid) return false;

  const admin = await Admin.findOne({ email }).lean<AdminDoc>();
  if (!admin) return false;

  const hashed = await hashPassword(password);
  const userId = String(admin._id);
  await Admin.findByIdAndUpdate(userId, { $set: { password: hashed } });
  await revokeAllTokensForUser(userId);
  return true;
}

/* ------------------------------------------------------------------ *
 * Details / list / update
 *
 * NB: admin password reset reuses the user-OTP layout (key=otp, value=email);
 * legacy `generate_otp_admin_password` / `verify_otp_admin` behave identically
 * to the user flow, so the pinned `storeUserOtp`/`verifyUserOtp` seam is exact.
 * ------------------------------------------------------------------ */

/** Resolve an Admin doc from an access-token inner id (legacy join via accessToken row). */
async function resolveAdminByInnerToken(innerId: string): Promise<AdminDoc | null> {
  const row = await getAccessTokenRow(innerId);
  if (!row || typeof row === "string") return null;
  const userId = String(row.userId ?? "");
  if (!userId) return null;
  return Admin.findById(userId).lean<AdminDoc>();
}

/**
 * Port of `get_admin_details_with_accessToken_service`: load the admin behind
 * the caller's access token. 404 when not found (route-level message).
 */
export async function getAdminDetails(innerId: string): Promise<NewAdminOut> {
  await db();
  const admin = await resolveAdminByInnerToken(innerId);
  if (!admin) {
    throw new HttpError(404, "Details not found");
  }
  return toNewAdminOut(admin);
}

/** Port of `get_all_admin_details_service` → all admins as NewAdminOut[]. */
export async function getAllAdminDetails(): Promise<NewAdminOut[]> {
  await db();
  const admins = await Admin.find().lean<AdminDoc[]>();
  return admins.map((doc) => toNewAdminOut(doc));
}

export interface AdminUpdateInput {
  firstName?: string;
  lastName?: string;
  avatar?: string;
}

/**
 * Port of `update_admin` + route: resolve the admin behind the token, apply the
 * profile update, and return the refreshed NewAdminOut. 404 when the admin is
 * gone (legacy raised inside update_admin).
 */
export async function updateAdmin(innerId: string, update: AdminUpdateInput): Promise<NewAdminOut> {
  await db();
  const admin = await resolveAdminByInnerToken(innerId);
  if (!admin) {
    throw new HttpError(404, "User Doesn't exist");
  }
  const userId = String(admin._id);

  // Legacy `update.model_dump(exclude=None)` — only set provided keys.
  const setOps: Record<string, unknown> = {};
  if (update.firstName !== undefined) setOps.firstName = update.firstName;
  if (update.lastName !== undefined) setOps.lastName = update.lastName;
  if (update.avatar !== undefined) setOps.avatar = update.avatar;
  if (Object.keys(setOps).length > 0) {
    await Admin.findByIdAndUpdate(userId, { $set: setOps });
  }

  const refreshed = await Admin.findById(userId).lean<AdminDoc>();
  if (!refreshed) {
    throw new HttpError(404, "User Doesn't exist");
  }
  return toNewAdminOut(refreshed);
}
