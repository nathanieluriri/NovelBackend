import { createHash, randomBytes } from "node:crypto";
import { db } from "@/lib/db";
import { env, envBool } from "@/lib/env";
import { HttpError } from "@/lib/http/errors";
import {
  User,
  Chapter,
  GoogleOAuthExchange,
  type UserDoc,
  type GoogleOAuthExchangeDoc,
} from "@/lib/models";
import { nowIso } from "@/lib/util/dates";

/**
 * Google OAuth (port of ../services/google_oauth_service.py +
 * ../core/google_oauth_config.py + ../repositories/google_oauth_repo.py —
 * see auth.md §6, sequence.md diagram 4).
 *
 * The OAuth `state` parameter carries the flow metadata
 * (`"v1." + base64url(JSON {t,n,r})`). Its random nonce `n` is ALSO written to a
 * short-lived HttpOnly+Secure+SameSite=Lax cookie when the flow starts, and the
 * callback rejects any `state` whose nonce does not match that cookie — this
 * binds the callback to the browser that initiated the flow and prevents login
 * CSRF. SameSite=Lax is sufficient here: the Google→backend callback is a
 * top-level GET navigation, on which Lax cookies are sent. The code exchange
 * against Google is done manually (the legacy already hand-rolls this).
 */

const GOOGLE_AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token";
const GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo";
const GOOGLE_OAUTH_SCOPE = "openid email profile";

const STATE_PREFIX = "v1."; // versioned base64-JSON states
const STATE_SEPARATOR = ":"; // legacy "<url-encoded-alias>:<nonce>" fallback
const MAX_REDIRECT_PATH_LENGTH = 512;

// Per-flow CSRF binding: the state nonce is mirrored into this cookie at
// /google/auth and verified at /google/callback.
const OAUTH_STATE_COOKIE = "oauth_state";
const OAUTH_STATE_COOKIE_MAX_AGE = 600; // seconds — the flow is short-lived

// ---------------------------------------------------------------------------
// Settings (lazy env reads — no top-level side effects)
// ---------------------------------------------------------------------------

type OAuthTarget = { alias: string; successUrl: string; errorUrl: string };

type GoogleOAuthSettings = {
  clientId: string;
  clientSecret: string;
  callbackUrl: string;
  redirectTargets: Record<string, OAuthTarget>;
  defaultTarget: string;
  exchangeTtlSeconds: number;
};

function isValidHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return (parsed.protocol === "http:" || parsed.protocol === "https:") && Boolean(parsed.host);
  } catch {
    return false;
  }
}

/** http/https URLs need a host; custom schemes (`myapp://login`) are allowed. */
function isValidFrontendRedirectUrl(value: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false; // no scheme / unparseable
  }
  if (parsed.protocol === "http:" || parsed.protocol === "https:") return Boolean(parsed.host);
  return Boolean(parsed.host || parsed.pathname);
}

function buildTarget(alias: string, successUrl: string, errorUrl: string): OAuthTarget | null {
  const success = successUrl.trim();
  const error = errorUrl.trim();
  if (!success || !error) return null;
  if (!isValidFrontendRedirectUrl(success) || !isValidFrontendRedirectUrl(error)) return null;
  return { alias, successUrl: success, errorUrl: error };
}

/** Supports both alias→url (string) and alias→{success,error} (object) forms. */
function parseTargetValue(alias: string, value: unknown): OAuthTarget | null {
  if (typeof value === "string") return buildTarget(alias, value, value);
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const obj = value as Record<string, unknown>;
  if (typeof obj.success !== "string" || typeof obj.error !== "string") return null;
  return buildTarget(alias, obj.success, obj.error);
}

function parseRedirectTargets(raw: string | undefined): Record<string, OAuthTarget> {
  if (!raw || !raw.trim()) return {};
  let decoded: unknown;
  try {
    decoded = JSON.parse(raw);
  } catch {
    return {};
  }
  if (!decoded || typeof decoded !== "object" || Array.isArray(decoded)) return {};
  const targets: Record<string, OAuthTarget> = {};
  for (const [key, value] of Object.entries(decoded as Record<string, unknown>)) {
    const alias = key.trim();
    if (!alias) continue;
    const target = parseTargetValue(alias, value);
    if (target) targets[alias] = target;
  }
  return targets;
}

/** Default 120 seconds, minimum 30. */
function parseExchangeTtlSeconds(raw: string | undefined): number {
  const parsed = parseInt((raw ?? "").trim(), 10);
  if (Number.isNaN(parsed)) return 120;
  return Math.max(parsed, 30);
}

function getGoogleOAuthSettings(): GoogleOAuthSettings {
  const redirectTargets = parseRedirectTargets(env("GOOGLE_OAUTH_REDIRECT_TARGETS"));
  let defaultTarget = (env("GOOGLE_OAUTH_DEFAULT_TARGET") ?? "").trim();
  const aliases = Object.keys(redirectTargets);
  if (!defaultTarget && aliases.length > 0) defaultTarget = aliases[0];
  return {
    clientId: (env("GOOGLE_CLIENT_ID") ?? "").trim(),
    clientSecret: (env("GOOGLE_CLIENT_SECRET") ?? "").trim(),
    callbackUrl: (env("GOOGLE_OAUTH_CALLBACK_URL") ?? "").trim(),
    redirectTargets,
    defaultTarget,
    exchangeTtlSeconds: parseExchangeTtlSeconds(env("GOOGLE_OAUTH_EXCHANGE_TTL_SECONDS")),
  };
}

function ensureConfigured(settings: GoogleOAuthSettings): void {
  const missing: string[] = [];
  if (!settings.clientId) missing.push("GOOGLE_CLIENT_ID");
  if (!settings.clientSecret) missing.push("GOOGLE_CLIENT_SECRET");
  if (!settings.callbackUrl) missing.push("GOOGLE_OAUTH_CALLBACK_URL");
  else if (!isValidHttpUrl(settings.callbackUrl)) {
    missing.push("GOOGLE_OAUTH_CALLBACK_URL (must be a valid http/https URL)");
  }
  if (Object.keys(settings.redirectTargets).length === 0) {
    missing.push("GOOGLE_OAUTH_REDIRECT_TARGETS");
  } else if (settings.defaultTarget && !settings.redirectTargets[settings.defaultTarget]) {
    missing.push("GOOGLE_OAUTH_DEFAULT_TARGET (must match a redirect target alias)");
  }
  if (missing.length) {
    throw new HttpError(500, `Google OAuth is not configured correctly: ${missing.join(", ")}`);
  }
}

function resolveTarget(
  settings: GoogleOAuthSettings,
  requestedAlias: string | undefined,
  invalidAliasStatus = 400,
): OAuthTarget {
  if (Object.keys(settings.redirectTargets).length === 0) {
    throw new HttpError(
      500,
      "Google OAuth is not configured correctly: GOOGLE_OAUTH_REDIRECT_TARGETS is not configured",
    );
  }
  const alias = (requestedAlias ?? settings.defaultTarget).trim();
  if (!alias) {
    throw new HttpError(
      500,
      "Google OAuth is not configured correctly: GOOGLE_OAUTH_DEFAULT_TARGET is not configured",
    );
  }
  const target = settings.redirectTargets[alias];
  if (!target) {
    throw new HttpError(invalidAliasStatus, `Unknown Google OAuth redirect target: ${alias}`);
  }
  return target;
}

// ---------------------------------------------------------------------------
// redirect_path sanitization + state encoding
// ---------------------------------------------------------------------------

/**
 * Anti-open-redirect: only relative paths rooted at the frontend origin are
 * accepted — must start with a single "/"; protocol-relative ("//evil.com"),
 * backslash, and encoded-slash variants are rejected; absolute URLs can never
 * pass the leading-"/" requirement.
 */
function sanitizeRedirectPath(raw: string | null | undefined): string | null {
  if (typeof raw !== "string") return null;
  const path = raw.trim();
  if (!path) return null;
  if (path.length > MAX_REDIRECT_PATH_LENGTH) return null;
  if (!path.startsWith("/")) return null;
  if (path.startsWith("//") || path.startsWith("/\\")) return null;
  if (path.toLowerCase().startsWith("/%2f")) return null;
  // A string starting with a single "/" cannot carry a scheme or authority
  // (the legacy urlparse scheme/netloc check is unreachable past this point).
  return path;
}

/** `"v1." + base64url(JSON {t,n,r})`; the caller supplies the crypto-random nonce. */
function encodeOauthState(targetAlias: string, nonce: string, redirectPath?: string | null): string {
  const payload: Record<string, string> = { t: targetAlias, n: nonce };
  if (redirectPath) payload.r = redirectPath;
  return STATE_PREFIX + Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function decodeOauthState(
  state: string | null,
): { target?: string; redirectPath?: string; nonce?: string } {
  if (!state) return {};
  if (state.startsWith(STATE_PREFIX)) {
    const body = state.slice(STATE_PREFIX.length);
    let payload: unknown;
    try {
      payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8"));
    } catch {
      return {};
    }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return {};
    const obj = payload as Record<string, unknown>;
    const result: { target?: string; redirectPath?: string; nonce?: string } = {};
    if (typeof obj.t === "string" && obj.t.trim()) result.target = obj.t.trim();
    if (typeof obj.n === "string" && obj.n.trim()) result.nonce = obj.n.trim();
    const redirectPath = sanitizeRedirectPath(typeof obj.r === "string" ? obj.r : null);
    if (redirectPath) result.redirectPath = redirectPath;
    return result;
  }
  // Legacy format: "<url-encoded-alias>:<nonce>" — accepted so in-flight
  // redirects from older builds keep working.
  const sepIndex = state.indexOf(STATE_SEPARATOR);
  if (sepIndex <= 0) return {};
  try {
    const alias = decodeURIComponent(state.slice(0, sepIndex)).trim();
    return alias ? { target: alias } : {};
  } catch {
    return {};
  }
}

// ---------------------------------------------------------------------------
// Frontend handoff redirects
// ---------------------------------------------------------------------------

function appendQueryParams(url: string, params: Record<string, string>): string {
  const parsed = new URL(url);
  for (const [key, value] of Object.entries(params)) parsed.searchParams.set(key, value);
  return parsed.toString();
}

function normalizeErrorCode(value: string | null | undefined): string {
  if (!value) return "google_oauth_failed";
  return value.trim().toLowerCase().replace(/ /g, "_");
}

/** Read a single cookie value from the request's Cookie header. */
function readCookie(req: Request, name: string): string | null {
  const header = req.headers.get("cookie");
  if (!header) return null;
  for (const part of header.split(";")) {
    const idx = part.indexOf("=");
    if (idx === -1) continue;
    if (part.slice(0, idx).trim() === name) return part.slice(idx + 1).trim();
  }
  return null;
}

function setStateCookie(nonce: string): string {
  return `${OAUTH_STATE_COOKIE}=${nonce}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${OAUTH_STATE_COOKIE_MAX_AGE}`;
}

function clearStateCookie(): string {
  return `${OAUTH_STATE_COOKIE}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`;
}

/** 302 redirect with an optional Set-Cookie (Response.redirect can't carry headers). */
function buildRedirect(location: string, setCookie?: string): Response {
  const headers = new Headers({ Location: location });
  if (setCookie) headers.append("Set-Cookie", setCookie);
  return new Response(null, { status: 302, headers });
}

function redirectSuccess(target: OAuthTarget, code: string, redirectPath?: string): Response {
  const params: Record<string, string> = { code };
  if (redirectPath) params.redirect_path = redirectPath;
  // Clear the per-flow nonce cookie on the way out.
  return buildRedirect(appendQueryParams(target.successUrl, params), clearStateCookie());
}

function redirectError(target: OAuthTarget, errorCode: string, redirectPath?: string): Response {
  const params: Record<string, string> = { error: normalizeErrorCode(errorCode) };
  if (redirectPath) params.redirect_path = redirectPath;
  return buildRedirect(appendQueryParams(target.errorUrl, params), clearStateCookie());
}

// ---------------------------------------------------------------------------
// Manual code exchange (the legacy fallback path, promoted to primary)
// ---------------------------------------------------------------------------

/**
 * Decode the id_token payload WITHOUT signature verification — justified: the
 * token was just fetched over TLS from Google's token endpoint using our
 * client secret, so the transport authenticates the source (legacy rationale).
 */
function decodeIdTokenPayload(idToken: string): Record<string, unknown> {
  const parts = idToken.split(".");
  if (parts.length !== 3) return {};
  try {
    const data: unknown = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8"));
    if (data && typeof data === "object" && !Array.isArray(data)) {
      return data as Record<string, unknown>;
    }
    return {};
  } catch {
    return {};
  }
}

async function fetchGoogleTokens(
  settings: GoogleOAuthSettings,
  code: string,
): Promise<Record<string, unknown> | null> {
  try {
    const resp = await fetch(GOOGLE_TOKEN_ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code,
        client_id: settings.clientId,
        client_secret: settings.clientSecret,
        redirect_uri: settings.callbackUrl,
        grant_type: "authorization_code",
      }).toString(),
    });
    if (!resp.ok) return null;
    const data: unknown = await resp.json();
    if (data && typeof data === "object" && !Array.isArray(data)) {
      return data as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

async function fetchUserinfoFallback(accessToken: string): Promise<Record<string, unknown> | null> {
  try {
    const resp = await fetch(GOOGLE_USERINFO_ENDPOINT, {
      headers: { authorization: `Bearer ${accessToken}` },
    });
    if (!resp.ok) return null;
    const data: unknown = await resp.json();
    if (data && typeof data === "object" && !Array.isArray(data)) {
      return data as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// User upsert (auth.md §6.3)
// ---------------------------------------------------------------------------

function extractProfileValue(info: Record<string, unknown>, key: string): string | null {
  const value = info[key];
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed) return trimmed;
  }
  return null;
}

function buildProfileUpdates(
  existing: UserDoc,
  info: Record<string, unknown>,
): Record<string, string> {
  const updates: Record<string, string> = {};
  const firstName = extractProfileValue(info, "given_name");
  const lastName = extractProfileValue(info, "family_name");
  const avatar = extractProfileValue(info, "picture");
  if (firstName && !existing.firstName) updates.firstName = firstName;
  if (lastName && !existing.lastName) updates.lastName = lastName;
  if (avatar && !existing.avatar) updates.avatar = avatar;
  return updates;
}

async function getOrCreateGoogleUser(info: Record<string, unknown>): Promise<UserDoc> {
  const email = extractProfileValue(info, "email");
  if (!email) throw new HttpError(400, "Google account email is missing");
  if (info.email_verified === false) {
    throw new HttpError(400, "Google account email is not verified");
  }

  await db();
  const existing = await User.findOne({ email }).lean<UserDoc>();
  if (existing) {
    const profileUpdates = buildProfileUpdates(existing, info);
    const updateSpec: Record<string, unknown> = { $addToSet: { authProviders: "google" } };
    if (Object.keys(profileUpdates).length) updateSpec.$set = profileUpdates;
    const updated = await User.findByIdAndUpdate(existing._id, updateSpec, { new: true }).lean<UserDoc>();
    if (!updated) throw new HttpError(404, "User not found");
    return updated;
  }

  // Legacy NewUserCreate defaults: new users start with chapter 1 unlocked.
  const chapterOne = await Chapter.findOne({ number: 1 }).select({ _id: 1 }).lean<{ _id: unknown }>();
  const created = await User.create({
    provider: "google",
    email,
    password: null,
    googleAccessToken: null,
    firstName: extractProfileValue(info, "given_name"),
    lastName: extractProfileValue(info, "family_name"),
    avatar: extractProfileValue(info, "picture"),
    authProviders: ["google"],
    unlockedChapters: chapterOne ? [String(chapterOne._id)] : [],
    dateCreated: nowIso(),
  });
  return created.toObject() as UserDoc;
}

// ---------------------------------------------------------------------------
// Public surface
// ---------------------------------------------------------------------------

function sha256Hex(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

/**
 * GET /user/google/auth — 302 to Google's consent screen. The sanitized
 * redirect_path and target alias travel in `state`.
 */
export async function buildGoogleAuthRedirect(
  target?: string,
  redirectPath?: string,
): Promise<Response> {
  const settings = getGoogleOAuthSettings();
  ensureConfigured(settings);
  const resolvedTarget = resolveTarget(settings, target, 400);
  const sanitizedRedirectPath = sanitizeRedirectPath(redirectPath);
  const nonce = randomBytes(24).toString("base64url");
  const state = encodeOauthState(resolvedTarget.alias, nonce, sanitizedRedirectPath);

  const url = new URL(GOOGLE_AUTHORIZE_ENDPOINT);
  url.searchParams.set("client_id", settings.clientId);
  url.searchParams.set("redirect_uri", settings.callbackUrl);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", GOOGLE_OAUTH_SCOPE);
  url.searchParams.set("state", state);
  // Bind the flow to this browser: mirror the state nonce into an HttpOnly cookie.
  return buildRedirect(url.toString(), setStateCookie(nonce));
}

/**
 * GET /user/google/callback — exchanges the authorization code, upserts the
 * user, mints a one-time exchange code, and 302s to the frontend target's
 * success_url (`?code=...&redirect_path=...`) or error_url (`?error=...`).
 */
export async function handleGoogleCallback(req: Request): Promise<Response> {
  const settings = getGoogleOAuthSettings();
  ensureConfigured(settings);

  const searchParams = new URL(req.url).searchParams;
  const statePayload = decodeOauthState(searchParams.get("state"));
  const stateAlias =
    statePayload.target && settings.redirectTargets[statePayload.target]
      ? statePayload.target
      : undefined;
  const redirectPath = statePayload.redirectPath;
  const target = resolveTarget(settings, stateAlias, 500);

  // Login-CSRF defense. Two modes, selected by OAUTH_STRICT_STATE:
  //  - default (false): PARITY mode. Legacy handle_google_oauth_callback treats
  //    the per-flow cookie as optional and falls back to the validated `state`
  //    payload + manual code exchange when the cookie is dropped (cross-site
  //    SameSite stripping, reverse-proxy stripping, HTTPS downgrade) — auth.md §6
  //    "keep the session optional ... robust to dropped cookies". So we fail OPEN
  //    on a missing cookie and reject only on a POSITIVELY mismatched cookie.
  //  - OAUTH_STRICT_STATE=true: HARDENED mode. The cookie is MANDATORY and must
  //    match the state nonce — full login-CSRF binding, at the cost of failing
  //    closed when a browser drops the cookie. Enable once you've confirmed your
  //    frontend flow reliably preserves the oauth_state cookie.
  const cookieNonce = readCookie(req, OAUTH_STATE_COOKIE);
  const strictState = envBool("OAUTH_STRICT_STATE", false);
  if (strictState) {
    if (!cookieNonce || !statePayload.nonce || cookieNonce !== statePayload.nonce) {
      return redirectError(target, "invalid_oauth_state", redirectPath);
    }
  } else if (cookieNonce && statePayload.nonce && cookieNonce !== statePayload.nonce) {
    return redirectError(target, "invalid_oauth_state", redirectPath);
  }

  const callbackError = searchParams.get("error");
  if (callbackError) return redirectError(target, callbackError, redirectPath);

  const authorizationCode = searchParams.get("code");
  if (!authorizationCode) {
    return redirectError(target, "missing_authorization_code", redirectPath);
  }

  const tokens = await fetchGoogleTokens(settings, authorizationCode);
  if (!tokens) return redirectError(target, "google_oauth_failed", redirectPath);

  let userInfo: Record<string, unknown> | null = null;
  if (typeof tokens.id_token === "string") {
    const decoded = decodeIdTokenPayload(tokens.id_token);
    if (Object.keys(decoded).length) userInfo = decoded;
  }
  if (!userInfo && typeof tokens.access_token === "string") {
    userInfo = await fetchUserinfoFallback(tokens.access_token);
  }
  if (!userInfo) return redirectError(target, "missing_google_userinfo", redirectPath);

  let user: UserDoc;
  try {
    user = await getOrCreateGoogleUser(userInfo);
  } catch (err) {
    if (err instanceof HttpError) return redirectError(target, err.message, redirectPath);
    throw err;
  }

  // One-time code: 32-byte url-safe random; only its sha256 hash is stored.
  const code = randomBytes(32).toString("base64url");
  await db();
  await GoogleOAuthExchange.create({
    codeHash: sha256Hex(code),
    userId: String(user._id),
    targetAlias: target.alias,
    createdAt: new Date(),
    expiresAt: new Date(Date.now() + settings.exchangeTtlSeconds * 1000),
    consumedAt: null,
  });

  return redirectSuccess(target, code, redirectPath);
}

/**
 * POST /user/google/exchange — atomic single-use consume: findOneAndUpdate
 * matching codeHash + consumedAt:null + expiresAt > now, setting consumedAt.
 */
export async function exchangeGoogleCode(code: string): Promise<{ userId: string }> {
  await db();
  const now = new Date();
  const record = await GoogleOAuthExchange.findOneAndUpdate(
    { codeHash: sha256Hex(typeof code === "string" ? code : ""), consumedAt: null, expiresAt: { $gt: now } },
    { $set: { consumedAt: now } },
    { new: false },
  ).lean<GoogleOAuthExchangeDoc>();
  if (!record) {
    throw new HttpError(401, "Google OAuth code is invalid, expired, or already used");
  }
  return { userId: String(record.userId) };
}
