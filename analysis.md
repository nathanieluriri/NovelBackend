# Project Gap Analysis

This review focuses on the requirements you listed: storing books/chapters/pages with comments and bookmarks for each entity, enforcing free vs paid access, and using Flutterwave webhooks to verify payments.

## Access control and subscription/paid flow gaps
- No explicit access model for chapters (free vs subscription vs paid-per-chapter). The only field that could represent this is `status` on chapters, but it is a free-form string and not enforced anywhere (`schemas/chapter_schema.py`, `services/chapter_services.py`, `api/v1/chapter.py`).
- Page retrieval does not check chapter access at all. `/page/get/{chapterId}` and `/page/get/page/{pageId}` return content for any authenticated user without verifying subscription or unlocked chapters (`api/v1/page.py`, `services/page_services.py`).
- The `pay-chapter` route currently requires an active subscription and ignores the bundle/price, so it does not support a paid-per-chapter model (`api/v1/payment.py`, `services/payment_service.py`).
- There is code for star-based chapter purchase in `create_transaction(..., TransactionType.chapter_purchase)`, but no API route calls it, so users cannot actually pay with stars to unlock a chapter (`services/payment_service.py`).
- No link between a chapter and the payment required to unlock it (no `chapter.priceBundleId` or similar), so even if payment is verified, the system does not know which chapters to unlock (`schemas/chapter_schema.py`, `api/v1/payment.py`).

## Payment webhook verification gaps
- The webhook trusts the payload after only checking `verif-hash`; it does not verify amount, currency, or transaction details with Flutterwave's verify API. That means a forged payload could credit stars or subscriptions if the secret leaks (`api/v1/payment.py`, `services/payment_service.py`).
- Webhook processing only credits star balance or subscription. There is no workflow to unlock a specific chapter after a successful payment, so "paid for a chapter" is not implemented (`api/v1/payment.py`, `services/payment_service.py`).

## Content interactions (comments/bookmarks) do not exist for each entity
- Comments are only implemented for chapters; there are no models or routes to comment on books or pages (`schemas/comments_schema.py`, `api/v1/comments.py`).
- Bookmarks are only implemented for pages; there are no bookmarks for books or chapters (`schemas/bookmark_schema.py`, `api/v1/bookmark.py`).

## Retrieval and authorization gaps
- All `/book/*` routes are admin-only because the router is included with `verify_admin_token`, so regular users cannot list or read books (`main.py`). This conflicts with "retrieve whatever is needed properly" for readers.
- Bookmark endpoints do not use auth at all, so any caller can create or read bookmarks for any userId (`api/v1/bookmark.py`). This breaks per-user access expectations.

## Data integrity and cleanup gaps
- Deleting a chapter does not reliably delete its pages because `delete_pages_by_chapter_id` filters on `chapter_id` (snake case) while pages store `chapterId` (camel case), leaving orphaned pages (`repositories/page_repo.py`, `services/chapter_services.py`).
- Deleting chapters or books does not clean up comments, likes, or bookmarks, so related data remains orphaned (`services/book_services.py`, `services/chapter_services.py`, `repositories/comments_repo.py`, `repositories/like_repo.py`, `repositories/bookmark_repo.py`).

## What you likely need to add
- A clear chapter access model (e.g., `accessType: free|subscription|paid`, `priceBundleId`, optional `freeUntil`), plus validation as enums in `schemas/chapter_schema.py`.
- An access check in chapter/page read endpoints to allow:
  - free chapters, or
  - subscription-active users, or
  - users who purchased/unlocked the chapter.
- A paid-per-chapter purchase flow that ties a payment bundle + chapterId together, unlocks the chapter on verified webhook, and uses idempotency.
- Comments and bookmarks for books and pages if you truly need them for each entity.
- Cleanup hooks on delete to remove comments/likes/bookmarks/pages consistently.
- Fix the page deletion filter to use `chapterId` so chapter deletes are consistent.
