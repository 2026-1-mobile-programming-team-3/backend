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

# api-spec §6.1: link 도메인 기반 매체명 매핑.
# 화이트리스트에 없으면 도메인을 그대로 publisher로 노출한다.
_PUBLISHER_MAP = {
    "n.news.naver.com": "네이버 뉴스",
    "news.naver.com": "네이버 뉴스",
    "siheung.go.kr": "시흥시청",
    "www.siheung.go.kr": "시흥시청",
}

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
        # image_url은 og:image 스크래핑 자리. 현재는 미구현 상태로 항상 null.
        image_url=None,
        category=_classify_category(f"{title} {summary}"),
        publisher=_extract_publisher(link),
    )


async def _fetch_naver_news(
    client: httpx.AsyncClient, query: str
) -> list[dict]:
    headers = {
        "X-Naver-Client-Id": settings.NAVER_API_ID,
        "X-Naver-Client-Secret": settings.NAVER_API_SECRET,
    }
    params = {"query": query, "display": 15, "sort": "date"}
    response = await client.get(_NAVER_NEWS_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("items", [])


async def _call_naver_api() -> list[NewsItem]:
    """네이버 뉴스 API를 두 쿼리로 병렬 호출하고 중복 제거 후 상위 20개를 반환한다."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await asyncio.gather(
                _fetch_naver_news(client, "시흥 반려동물"),
                _fetch_naver_news(client, "반려동물 정책 지원"),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="뉴스 데이터를 가져오는 데 실패했습니다.",
        ) from exc

    # link 기준 중복 제거
    seen: set[str] = set()
    unique_items: list[dict] = []
    for batch in results:
        for item in batch:
            link = item.get("link") or item.get("originallink", "")
            if link not in seen:
                seen.add(link)
                unique_items.append(item)

    news_items = [_build_news_item(raw) for raw in unique_items]
    # pubDate 내림차순 정렬 후 상위 20개
    news_items.sort(key=lambda x: x.published_date, reverse=True)
    return news_items[:20]


async def get_news_list(redis: aioredis.Redis) -> NewsListResponse:
    # Redis 캐시 조회 — 오류 시 API 직접 호출로 graceful degradation
    try:
        cached = await redis.get(_CACHE_KEY)
        if cached:
            return NewsListResponse(news=json.loads(cached))
    except Exception:
        cached = None

    news_items = await _call_naver_api()

    try:
        await redis.set(
            _CACHE_KEY,
            json.dumps([item.model_dump() for item in news_items]),
            ex=settings.NEWS_CACHE_TTL,
        )
    except Exception:
        pass  # 캐시 저장 실패는 응답에 영향을 주지 않는다

    return NewsListResponse(news=news_items)


async def get_news_detail(
    redis: aioredis.Redis, news_id: str
) -> NewsDetail:
    response = await get_news_list(redis)
    for item in response.news:
        if item.news_id == news_id:
            # 목록 데이터에서 detail 응답을 구성한다 (별도 본문 API 없음)
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
