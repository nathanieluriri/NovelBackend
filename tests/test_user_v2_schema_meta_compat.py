from schemas.listing_schema import ListMetaOut
from schemas.user_v2_schema import InteractionTotals, UserDetailsV2Out


def test_user_details_v2_accepts_list_meta_out_instances():
    payload = {
        "summary": InteractionTotals(totalLikes=1, totalBookmarks=2),
        "likes": [],
        "bookmarks": [],
        "likesMeta": ListMetaOut(skip=0, limit=100, returned=0, total=1, hasMore=True),
        "bookmarksMeta": ListMetaOut(skip=0, limit=100, returned=0, total=2, hasMore=True),
    }

    result = UserDetailsV2Out.model_validate(payload)

    assert result.likesMeta.total == 1
    assert result.bookmarksMeta.total == 2

