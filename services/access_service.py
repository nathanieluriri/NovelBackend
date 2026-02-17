from datetime import datetime, timezone

from repositories.entitlement_repo import has_chapter_entitlement
from schemas.chapter_schema import ChapterAccessType, ChapterOut
from schemas.user_schema import UserOut


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def is_subscription_active(subscription: dict | None) -> bool:
    if not subscription:
        return False
    if not subscription.get("active"):
        return False
    expires_at = _parse_datetime(subscription.get("expiresAt"))
    if not expires_at:
        return False
    return expires_at > datetime.now(timezone.utc)


async def is_chapter_unlocked(user: UserOut, chapter_id: str) -> bool:
    legacy_unlocked = bool(user.unlockedChapters and chapter_id in user.unlockedChapters)
    if legacy_unlocked:
        return True
    return await has_chapter_entitlement(userId=user.userId, chapterId=chapter_id)


async def has_chapter_access(user: UserOut, chapter: ChapterOut) -> bool:
    access_type = chapter.accessType or ChapterAccessType.free

    if access_type == ChapterAccessType.free:
        return True

    if access_type == ChapterAccessType.subscription:
        subscription = user.subscription.model_dump() if user.subscription else None
        return is_subscription_active(subscription)

    return await is_chapter_unlocked(user=user, chapter_id=chapter.id)
