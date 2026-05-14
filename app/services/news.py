import asyncio
import hashlib
import html
import json
import re
from datetime import date
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx
import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import news as news_crud
from app.schemas.news import (
    CalendarEventOut,
    CalendarMonthResponse,
    DailyEventOut,
    DailyEventsResponse,
    NewsDetail,
    NewsItem,
    NewsListResponse,
)

_NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
_CACHE_KEY = "news:list"
_OG_CACHE_PREFIX = "news:og:"
_OG_CACHE_TTL = 60 * 60 * 24  # 24h

# api-spec §6.1: link 도메인 기반 매체명 매핑.
_PUBLISHER_MAP = {
    "n.news.naver.com": "네이버 뉴스",
    "news.naver.com": "네이버 뉴스",
    "siheung.go.kr": "시흥시청",
    "www.siheung.go.kr": "시흥시청",
}

# 시흥 지역 키워드 — 시흥시 본문 또는 시흥시 산하 동 이름
_SIHEUNG_KEYWORDS = (
    "시흥", "정왕", "배곧", "목감", "능곡", "은행", "매화", "신천",
    "대야", "장곡", "연성", "월곶", "거모", "과림",
)

# 반려동물 키워드 — 매칭/지원/봉사가 반려동물 맥락임을 보장
_PET_KEYWORDS = (
    "반려", "펫", "강아지", "고양이", "유기견", "유기묘", "유기동물",
    "중성화", "동물병원", "동물보호", "동물복지", "댕댕", "반려동물",
    "TNR", "tnr", "동물등록",
)

# api-spec §6.1: 키워드 룰 분류. 첫 매칭 우선, 매칭 실패 시 POLICY 디폴트.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("EVENT", ("행사", "축제", "이벤트", "박람회", "마켓")),
    ("VOLUNTEER", ("봉사", "자원봉사")),
    ("BADGE", ("인증", "마크", "라벨")),
    ("SUPPORT", ("지원", "보조금", "수당", "수술비", "지원금")),
    ("POLICY", ("정책", "조례", "법", "제도", "고시", "규정")),
]


def _clean_html(text: str) -> str:
    """네이버 API 응답에 섞인 HTML 태그와 엔티티를 제거한다."""
    return re.sub(r"<[^>]+>", "", html.unescape(text)).strip()


def _parse_pub_date(rfc822: str) -> str:
    """RFC 822 날짜 문자열을 'YYYY-MM-DD' 형식으로 변환한다."""
    try:
        dt = parsedate_to_datetime(rfc822)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def _classify_category(text: str) -> str:
    for cat, keywords in _CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return cat
    return "POLICY"


def _extract_publisher(link: str) -> str:
    try:
        domain = urlparse(link).netloc
    except Exception:
        return ""
    return _PUBLISHER_MAP.get(domain, domain)


def _has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in text for kw in keywords)


# og:image 스크래핑용 정규식 — meta property/name 둘 다 매칭
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)\s*=\s*["\']og:image["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_IMAGE_RE_REV = re.compile(
    r'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]*(?:property|name)\s*=\s*["\']og:image["\']',
    re.IGNORECASE,
)
_TWITTER_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)\s*=\s*["\']twitter:image(?::src)?["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


async def _fetch_og_image(
    client: httpx.AsyncClient,
    redis: aioredis.Redis | None,
    link: str,
) -> str | None:
    """기사 페이지의 og:image / twitter:image meta 를 추출한다.

    실패·타임아웃·이미지 없음은 모두 None.
    Redis 캐시(24h) per-link 적용. 캐시 hit 시 빈 문자열은 "이전에 찾지 못함"을 의미.
    """
    if not link:
        return None

    cache_key = _OG_CACHE_PREFIX + hashlib.sha256(link.encode()).hexdigest()[:16]

    # 캐시 조회
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached is not None:
                val = cached.decode() if isinstance(cached, bytes) else cached
                return val or None
        except Exception:
            pass

    image_url: str | None = None
    try:
        resp = await client.get(
            link,
            timeout=4.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; SiheungGagae/1.0; +https://siheunggagae.app)"
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        if resp.status_code == 200:
            # 본문에서 og:image / twitter:image 추출 (head 영역 우선이지만 전체 검색이 안전)
            text = resp.text
            for pattern in (_OG_IMAGE_RE, _OG_IMAGE_RE_REV, _TWITTER_IMAGE_RE):
                m = pattern.search(text)
                if m:
                    candidate = html.unescape(m.group(1)).strip()
                    if candidate.startswith("//"):
                        candidate = "https:" + candidate
                    if candidate.startswith("http"):
                        image_url = candidate
                        break
    except Exception:
        image_url = None

    # 캐시 저장 — None 도 빈 문자열로 저장해 재시도 비용 절감
    if redis is not None:
        try:
            await redis.set(cache_key, image_url or "", ex=_OG_CACHE_TTL)
        except Exception:
            pass

    return image_url


def _build_news_item(raw: dict) -> NewsItem:
    link = raw.get("link") or raw.get("originallink", "")
    news_id = hashlib.sha256(link.encode()).hexdigest()[:12]
    title = _clean_html(raw.get("title", ""))
    summary = _clean_html(raw.get("description", ""))
    return NewsItem(
        news_id=news_id,
        title=title,
        summary=summary,
        published_date=_parse_pub_date(raw.get("pubDate", "")),
        link=link,
        image_url=None,  # 이후 _enrich_images() 에서 채움
        category=_classify_category(f"{title} {summary}"),
        publisher=_extract_publisher(link),
    )


async def _fetch_naver_news(
    client: httpx.AsyncClient, query: str, *, display: int = 20
) -> list[dict]:
    headers = {
        "X-Naver-Client-Id": settings.NAVER_API_ID,
        "X-Naver-Client-Secret": settings.NAVER_API_SECRET,
    }
    params = {"query": query, "display": display, "sort": "date"}
    try:
        response = await client.get(_NAVER_NEWS_URL, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("items", [])
    except httpx.HTTPError:
        # 개별 쿼리 실패는 전체 실패로 키우지 않는다 — 다른 쿼리 결과로 채움
        return []


async def _call_naver_api() -> list[NewsItem]:
    """여러 쿼리로 후보를 모은 뒤 시흥 ∩ 반려동물 키워드 필터링 후 상위 20개를 반환한다.

    - 1차: 시흥 키워드 + 반려동물 키워드를 모두 포함하는 기사만 채택
    - 부족하면(< 8개): 반려동물 키워드만 매칭되는 기사로 보충 (시흥시 사이트는 항상 우선)
    """
    # 다양한 조합으로 후보 풀 확보
    queries = (
        "시흥 반려동물",
        "시흥시 반려동물",
        "시흥 유기견 중성화",
        "시흥시 동물보호",
        "정왕동 반려동물",
        "반려동물 정책 지원",
        "반려동물 봉사",
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await asyncio.gather(
            *(_fetch_naver_news(client, q, display=20) for q in queries),
            return_exceptions=False,
        )

    # link 기준 중복 제거
    seen: set[str] = set()
    unique_raw: list[dict] = []
    for batch in results:
        for item in batch:
            link = item.get("link") or item.get("originallink", "")
            if not link or link in seen:
                continue
            seen.add(link)
            unique_raw.append(item)

    # 1차/2차 분류
    strict: list[dict] = []  # 시흥 ∩ 반려동물
    loose: list[dict] = []  # 반려동물 (시흥 없어도)
    for raw in unique_raw:
        title = _clean_html(raw.get("title", ""))
        summary = _clean_html(raw.get("description", ""))
        link = raw.get("link") or raw.get("originallink", "")
        text = f"{title} {summary} {link}"
        has_si = _has_keyword(text, _SIHEUNG_KEYWORDS)
        has_pet = _has_keyword(text, _PET_KEYWORDS)
        # 시흥시 공식 도메인은 펫 키워드 없어도 통과 (보도자료 자체가 반려 맥락일 가능성 高)
        is_official_siheung = "siheung.go.kr" in link
        if (has_si and has_pet) or is_official_siheung:
            strict.append(raw)
        elif has_pet:
            loose.append(raw)

    # strict 우선, 부족하면 loose로 보충 → 총 20개
    items_raw = strict[:]
    if len(items_raw) < 8:
        items_raw.extend(loose[: 20 - len(items_raw)])

    news_items = [_build_news_item(raw) for raw in items_raw[:20]]
    news_items.sort(key=lambda x: x.published_date, reverse=True)
    return news_items[:20]


async def _enrich_images(
    items: list[NewsItem], redis: aioredis.Redis | None
) -> list[NewsItem]:
    """각 기사 link 에서 og:image 를 병렬 스크래핑해 image_url 을 채운다."""
    if not items:
        return items
    async with httpx.AsyncClient() as client:
        images = await asyncio.gather(
            *(_fetch_og_image(client, redis, item.link) for item in items),
            return_exceptions=False,
        )
    enriched: list[NewsItem] = []
    for item, img in zip(items, images):
        enriched.append(item.model_copy(update={"image_url": img}))
    return enriched


async def get_news_list(redis: aioredis.Redis) -> NewsListResponse:
    # Redis 캐시 조회 — 오류 시 API 직접 호출로 graceful degradation
    try:
        cached = await redis.get(_CACHE_KEY)
        if cached:
            return NewsListResponse(news=json.loads(cached))
    except Exception:
        cached = None

    try:
        news_items = await _call_naver_api()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="뉴스 데이터를 가져오는 데 실패했습니다.",
        ) from exc

    # og:image 보강 — 실패해도 항목은 유지
    news_items = await _enrich_images(news_items, redis)

    try:
        await redis.set(
            _CACHE_KEY,
            json.dumps([item.model_dump() for item in news_items]),
            ex=settings.NEWS_CACHE_TTL,
        )
    except Exception:
        pass

    return NewsListResponse(news=news_items)


async def get_news_detail(
    redis: aioredis.Redis, news_id: str
) -> NewsDetail:
    response = await get_news_list(redis)
    for item in response.news:
        if item.news_id == news_id:
            return NewsDetail(
                news_id=item.news_id,
                title=item.title,
                content=item.summary,
                official_link=item.link,
                published_date=item.published_date,
                image_url=item.image_url,
                category=item.category,
                publisher=item.publisher,
            )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="해당 뉴스를 찾을 수 없습니다.",
    )


async def get_calendar_events_by_month(
    db: AsyncSession, year: int, month: int
) -> CalendarMonthResponse:
    events = await news_crud.get_calendar_events(db, year, month)
    return CalendarMonthResponse(
        events=[
            CalendarEventOut(
                event_id=ev.id,
                title=ev.title,
                start_date=ev.start_date.isoformat(),
                end_date=ev.end_date.isoformat(),
            )
            for ev in events
        ]
    )


async def get_daily_events(
    db: AsyncSession, date_str: str
) -> DailyEventsResponse:
    try:
        target = date.fromisoformat(date_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요.",
        ) from exc

    events = await news_crud.get_daily_events(db, target)
    return DailyEventsResponse(
        daily_events=[
            DailyEventOut(
                event_id=ev.id,
                title=ev.title,
                description=ev.description,
                time=ev.event_time.strftime("%H:%M") if ev.event_time else None,
            )
            for ev in events
        ]
    )
