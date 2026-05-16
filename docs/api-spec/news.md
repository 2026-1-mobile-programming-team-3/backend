# API 명세서 — 반려동물 뉴스 캘린더 (News)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/news.py` (prefix `/news`, tag `News`).

> 뉴스 본문 데이터는 네이버 뉴스 검색 API + og:image 스크래핑으로 Redis 캐시(4h/24h)에서 제공한다 — DB `news` 테이블은 존재하지 않는다. 캘린더는 `calendar_events` 테이블 기반.

---

## 6. 반려동물 뉴스 캘린더 (News)

### 6.1 정책 뉴스 목록 조회 — `GET /news` [T0]

**인증 불필요**

**Response — 200 OK**

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| news_id | string | 12자 hex (네이버 link의 sha256 prefix) |
| title | string | HTML 태그·엔티티 제거된 제목 |
| summary | string | HTML 태그·엔티티 제거된 요약 |
| published_date | string | `YYYY-MM-DD` |
| link | string | 네이버 뉴스 viewer URL (원문 링크) |
| image_url | string \| null | 본문 og:image 백엔드 스크래핑 결과. 실패 시 `null` |
| category | string | 키워드 룰 분류. `POLICY` / `EVENT` / `VOLUNTEER` / `BADGE` / `SUPPORT` |
| publisher | string | 매체명. link 도메인에서 추출 + 화이트리스트 매핑 (예: `n.news.naver.com → 네이버 뉴스`, `siheung.go.kr → 시흥시청`) |

```json
{
  "news": [
    {
      "news_id": "abc123def456",
      "title": "2026년 실외 사육견 중성화 수술비 지원 안내",
      "summary": "시흥시 거주 취약계층 대상...",
      "published_date": "2026-04-10",
      "link": "https://n.news.naver.com/article/...",
      "image_url": "https://imgnews.pstatic.net/image/.../article.jpg",
      "category": "POLICY",
      "publisher": "네이버 뉴스"
    }
  ]
}
```

> 네이버 뉴스 검색 API를 호출해 시흥 반려동물 + 정책 키워드로 조합. Redis 4시간 캐시.
> `image_url`은 og:image 스크래핑 + Redis 24h 캐시. 스크래핑 실패/타임아웃 시 `null`.
> `category`는 본문/제목 키워드 룰로 분류 — 매칭 실패 시 `POLICY` 디폴트.

---

### 6.2 정책 뉴스 상세 조회 — `GET /news/{news_id}` [T1]

**인증 불필요** / **Path**: `news_id` (string, 12자 hex)

**Response — 200 OK**
```json
{
  "news_id": "abc123def456",
  "title": "2026년 실외 사육견 중성화 수술비 지원 안내",
  "content": "시흥시는 무분별한 개체수 증가를 막기 위해...",
  "official_link": "https://n.news.naver.com/article/...",
  "published_date": "2026-04-10",
  "image_url": "https://imgnews.pstatic.net/image/.../article.jpg",
  "category": "POLICY",
  "publisher": "네이버 뉴스"
}
```

> 네이버 뉴스 API는 본문을 제공하지 않으므로 `content`는 6.1의 `summary`와 동일. `official_link`는 6.1의 `link`와 동일. `image_url` / `category` / `publisher`는 6.1과 같은 값.

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 404 | 캐시에 해당 `news_id` 없음 |

---

### 6.3 월별 정책 일정 캘린더 조회 — `GET /news/calendar` [T1]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| year | integer | Y | 조회할 연도 (예: 2026) |
| month | integer | Y | 조회할 월 (1~12) |

**Response — 200 OK**
```json
{
  "events": [
    {
      "event_id": 10,
      "title": "중성화 지원사업 신청 마감",
      "start_date": "2026-05-15",
      "end_date": "2026-05-15"
    }
  ]
}
```

---

### 6.4 특정 일자 정책 상세 일정 조회 — `GET /news/calendar/daily` [T2]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| date | string | Y | 날짜 (`YYYY-MM-DD`) |

**Response — 200 OK**
```json
{
  "daily_events": [
    {
      "event_id": 10,
      "title": "중성화 지원사업 신청 마감",
      "description": "동 행정복지센터 방문 접수 마감일입니다.",
      "time": "18:00"
    }
  ]
}
```
