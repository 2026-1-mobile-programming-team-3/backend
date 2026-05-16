# API 명세서 — 홈 대시보드 (Home)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/home.py` (prefix `/home`, tag `Home`).

---

## 1. 홈 대시보드 조회 — `GET /home/dashboard` [T0]

홈 화면 진입 시 필요한 어그리게이트 데이터(사용자 컨텍스트, 산책지수, 날씨, 매장 카운트, 매칭 요약, 알림 카운트)를 1회 호출로 반환.

**인증 필요**

### Query Parameters
없음. 인증된 사용자의 `region_si` / `region_dong` 기준으로 서버가 산출.

### Response — 200 OK
```json
{
  "user": {
    "nickname": "댕댕이주인",
    "role": "USER",
    "region_si": "시흥시",
    "region_dong": "정왕동"
  },
  "walk_score": 92,
  "weather": {
    "condition": "CLEAR",
    "temp_c": 18.0,
    "dust_grade": "GOOD",
    "source": "stub"
  },
  "nearby_store_count": 24,
  "my_match_summary": {
    "as_author": {
      "match_id": 1,
      "title": "정왕동 실외견 병원 이동 부탁드립니다",
      "desired_date": "2026-05-10",
      "status": "WAITING",
      "applications_count": 2
    },
    "as_applicant": null
  },
  "volunteer_stats": null,
  "unread_notification_count": 1,
  "generated_at": "2026-05-13T09:00:00Z"
}
```

- `walk_score`: 0~100 정수. `region_dong` 미설정 시 `null`. **TTL 30분** Redis 캐시.
- `weather.condition` enum: `CLEAR / CLOUDY / RAIN / SNOW`.
- `weather.dust_grade` enum: `GOOD / NORMAL / BAD / VERY_BAD`.
- `weather.source`: 외부 API 미연동 시 `"stub"`. 연동 후 `"live"`.
- `weather`: `region_dong` 미설정 시 `null`. **TTL 30분** Redis 캐시.
- `nearby_store_count`: `region_dong` 부분 일치 매장 수. **TTL 5분** Redis 캐시.
- `volunteer_stats`: 역할이 `VOLUNTEER` 또는 `ADMIN`인 경우에만 `{ total_count, avg_rating }`. 일반 사용자는 `null`.
- `my_match_summary.as_author` / `as_applicant`: 본인 작성/신청 매칭 중 `status != DONE` 의 최신 1건. 없으면 `null`.

### Errors

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |

> ⚠️ `walk_score` / `weather` 는 외부 API 미연동 상태로 현재 stub 응답을 반환한다. 응답 내 `source:"stub"` 표기를 클라이언트가 인지하면 노출 정책을 조정할 수 있다.
