# API 명세서 — 반려동물 뉴스 캘린더 (News)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

---

## 6. 반려동물 뉴스 캘린더 (News)

### 6.1 정책 뉴스 목록 조회 — `GET /news` [T0]

**인증 불필요**

**Response — 200 OK**
```json
{
  "news": [
    {
      "news_id": 1,
      "title": "2026년 실외 사육견 중성화 수술비 지원 안내",
      "summary": "시흥시 거주 취약계층 대상...",
      "published_date": "2026-04-10"
    }
  ]
}
```

---

### 6.2 정책 뉴스 상세 조회 — `GET /news/{newsId}` [T1]

**인증 불필요** / **Path**: `newsId` (integer)

**Response — 200 OK**
```json
{
  "news_id": 1,
  "title": "2026년 실외 사육견 중성화 수술비 지원 안내",
  "content": "시흥시는 무분별한 개체수 증가를 막기 위해... (전체 본문)",
  "official_link": "https://www.siheung.go.kr/...",
  "published_date": "2026-04-10"
}
```

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
