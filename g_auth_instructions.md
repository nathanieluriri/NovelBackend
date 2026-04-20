# Google OAuth — Frontend Integration Guide

This document describes how to start a Google sign-in from a frontend, how to
pick the correct return environment, and how to send the user back to the
exact page they were on when their session expired.

## Endpoints

| Method | Path                              | Purpose                                                       |
| ------ | --------------------------------- | ------------------------------------------------------------- |
| GET    | `/api/v1/user/google/auth`        | Start the Google OAuth flow. Redirects the browser to Google. |
| GET    | `/api/v1/user/google/callback`    | Google's redirect target. Sends the user back to the frontend with a one-time `code` (or `error`). |
| POST   | `/api/v1/user/google/exchange`    | Exchange the one-time `code` for the authenticated user payload (access + refresh tokens). |

## Starting the flow

```
GET /api/v1/user/google/auth?target=<env>&redirect_path=<relative-path>
```

### `target` (query param, enum)

Tells the backend which frontend environment to send the user back to after
login. Must be one of the registered aliases:

| Enum value | Typical deployment |
| ---------- | ------------------ |
| `local`    | Local dev (`http://localhost:3001`)              |
| `dev`      | Sandbox / preview builds                         |
| `staging`  | Pre-prod                                         |
| `prod`     | Production                                       |

The actual success/error URLs for each alias come from the `GOOGLE_OAUTH_REDIRECT_TARGETS`
environment variable. If `target` is omitted, the backend uses `GOOGLE_OAUTH_DEFAULT_TARGET`.

Unknown values are rejected by FastAPI with a `422` before any work is done.

### `redirect_path` (query param, optional)

Relative path on the frontend that the user should be returned to **after** a
successful login. Useful when a user is silently logged out (token expired,
403, etc.) and you want to drop them back on `/settings/profile`, `/library`,
or whichever page they started from.

Constraints (enforced server-side):

- Must start with a single `/` (e.g. `/settings`, `/books/123?tab=reviews`).
- Must be purely relative — no scheme, no host, no userinfo.
- Max length 512 characters.
- Protocol-relative paths (`//evil.com/x`), backslash tricks (`/\evil.com`),
  and encoded double-slash (`/%2fevil.com`) are rejected to avoid open-redirect
  attacks.

If the value fails validation it is silently dropped; the rest of the flow
still works, the user just lands on the default post-login page.

## What the frontend receives

On **success**, the user is redirected to the `success_url` of the selected
target with:

```
<success_url>?code=<one-time-code>&redirect_path=<the-path-you-sent-in>
```

On **error**, the user is redirected to the `error_url` with:

```
<error_url>?error=<error_code>&redirect_path=<the-path-you-sent-in>
```

`redirect_path` is only appended when it was originally supplied and passed
validation. Frontends should treat its absence as "fall back to the default
landing page".

The `code` is a single-use token valid for `GOOGLE_OAUTH_EXCHANGE_TTL_SECONDS`
(default 120s). Exchange it immediately:

```http
POST /api/v1/user/google/exchange
Content-Type: application/json

{ "code": "<one-time-code>" }
```

The response contains the authenticated user plus tokens. Persist them, then
navigate the user to `redirect_path` if present, otherwise your usual
post-login route.

## End-to-end frontend example

```ts
// 1. Kick off login. Capture the current path so we can come back to it.
function startGoogleLogin() {
  const target = import.meta.env.VITE_OAUTH_TARGET as
    | "local" | "dev" | "staging" | "prod";
  const redirectPath = window.location.pathname + window.location.search;
  const qs = new URLSearchParams({ target, redirect_path: redirectPath });
  window.location.href = `${API_BASE}/api/v1/user/google/auth?${qs}`;
}

// 2. On the success page mounted at <success_url>, exchange the code and
//    navigate to redirect_path if present.
async function completeGoogleLogin() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  const redirectPath = params.get("redirect_path");

  if (!code) {
    navigate("/login?error=missing_code");
    return;
  }

  const res = await fetch(`${API_BASE}/api/v1/user/google/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    navigate("/login?error=exchange_failed");
    return;
  }
  const user = await res.json();
  saveTokens(user.accessToken, user.refreshToken);

  // Only trust redirect_path if it's a relative app route — never use it
  // verbatim on window.location.href because a malicious intermediary could
  // have swapped the URL. Defence-in-depth even though the backend also
  // validates.
  const safeRedirect =
    redirectPath && redirectPath.startsWith("/") && !redirectPath.startsWith("//")
      ? redirectPath
      : "/";
  navigate(safeRedirect);
}

// 3. On the error page mounted at <error_url>.
function showGoogleLoginError() {
  const params = new URLSearchParams(window.location.search);
  const error = params.get("error") ?? "unknown";
  const retryPath = params.get("redirect_path");
  // Surface the error, offer a "Try again" that re-runs startGoogleLogin()
  // with `redirect_path` preserved so the user ends up where they intended.
}
```

## How it survives session loss

Both `target` and `redirect_path` are embedded into the OAuth `state` parameter
(a versioned, base64-encoded JSON blob). Google returns `state` to the callback
as a query parameter, so the backend can recover both values even when the
session cookie is lost during the round-trip (cross-site SameSite quirks,
reverse proxies, HTTPS downgrades, etc.). The session is still written as a
secondary fallback for backwards compatibility.

This means:

- `?target=prod` will always return the user to the prod frontend.
- `?redirect_path=/settings` will always be preserved, even across a cookie
  drop, a `MismatchingStateError`, or a Google-side `access_denied`.

## Security notes

- `redirect_path` is validated on **both** the outbound leg (at `/google/auth`)
  and the inbound leg (when decoding `state` in `/google/callback`). Hand-forged
  `state` blobs with absolute URLs are silently stripped.
- Always re-validate on the frontend before calling `navigate()` — treat
  `redirect_path` as untrusted input in depth.
- The one-time `code` returned to the frontend is SHA-256 hashed server-side,
  single-use, and expires quickly. Never log it.

## Environment variables

| Variable                              | Purpose                                                                 |
| ------------------------------------- | ----------------------------------------------------------------------- |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth client credentials.                                   |
| `GOOGLE_OAUTH_CALLBACK_URL`           | Fully-qualified URL of `/api/v1/user/google/callback` as registered in the Google console. |
| `GOOGLE_OAUTH_REDIRECT_TARGETS`       | JSON map of alias → `{"success": <url>, "error": <url>}` (or a single string that is used for both). |
| `GOOGLE_OAUTH_DEFAULT_TARGET`         | Alias used when the caller omits `target`. Recommended: set this explicitly. |
| `GOOGLE_OAUTH_EXCHANGE_TTL_SECONDS`   | Lifetime of the one-time exchange `code`. Defaults to 120.              |
| `SESSION_COOKIE_SAME_SITE` / `SESSION_COOKIE_HTTPS_ONLY` / `SESSION_COOKIE_DOMAIN` | Fine-tune cookie behaviour. Use `SameSite=None; Secure` whenever the frontend origin differs from the API origin. |

## Adding a new `target` value

1. Add a member to `GoogleOAuthTargetEnum` in `schemas/google_oauth_schema.py`.
2. Register the alias in `GOOGLE_OAUTH_REDIRECT_TARGETS` for every environment
   that must support it.
3. Deploy backend before pointing the frontend at the new alias.
