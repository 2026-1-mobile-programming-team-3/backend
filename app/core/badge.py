"""봉사 뱃지 등급 계산.

임계값 (마이페이지 명세):
- 새싹(SEED): 1건 이상
- 꽃(FLOWER): 3건 이상
- 열매(FRUIT): 8건 이상
- 나무(TREE): 15건 이상

0건은 NONE.
"""
from __future__ import annotations

from app.models.enums import VolunteerBadgeTier

# (다음 등급 이상이 되기 위한 최소 건수, 그 등급의 enum 값)
# 정렬: 임계값 오름차순.
_THRESHOLDS: list[tuple[int, VolunteerBadgeTier]] = [
    (1, VolunteerBadgeTier.SEED),
    (3, VolunteerBadgeTier.FLOWER),
    (8, VolunteerBadgeTier.FRUIT),
    (15, VolunteerBadgeTier.TREE),
]


def compute_badge(count: int) -> dict:
    """count → {tier, count, next_tier, next_threshold, progress_pct(0~100)}."""
    current_tier = VolunteerBadgeTier.NONE
    current_threshold = 0
    next_tier: VolunteerBadgeTier | None = None
    next_threshold: int | None = None

    for threshold, tier in _THRESHOLDS:
        if count >= threshold:
            current_tier = tier
            current_threshold = threshold
        else:
            next_tier = tier
            next_threshold = threshold
            break

    if next_threshold is None or next_threshold == current_threshold:
        progress = 100 if current_tier == VolunteerBadgeTier.TREE else 0
    else:
        span = next_threshold - current_threshold
        progress = max(0, min(100, int((count - current_threshold) * 100 / span)))

    return {
        "tier": current_tier,
        "count": count,
        "next_tier": next_tier,
        "next_threshold": next_threshold,
        "progress_pct": progress,
    }
