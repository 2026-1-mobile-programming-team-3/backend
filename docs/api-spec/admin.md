# API 명세서 — 관리자 (`/admin`)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/admin.py` (prefix `/admin`, tag `Admin`).

---

## 0. 관리자 권한 개요

### 0.1 사용자 등급 — `users.role`

| 값 | 의미 | 부여 방법 |
| --- | --- | --- |
| `USER` | 일반 사용자 | 회원가입 시 자동 |
| `VOLUNTEER` | 봉사자 | `POST /users/me/volunteer-request` 신청 → 본 문서 §1.2 의 `APPROVE` 처리 시 자동 승급 |
| `ADMIN` | 운영자 | **회원가입으로는 생성 불가.** 운영자가 SQLAdmin UI 에서 수동 부여 (§0.3) |

### 0.2 "이 요청자가 관리자인가?" 판단 흐름

- JWT(access token) 자체에는 `role` 이 들어 있지 않다 (`sub`(user_id) 만).
- 매 요청마다 `app/core/deps.py:get_current_admin` 의존성이 토큰 디코드 후 DB `users` 테이블을 다시 조회 → 그 행의 `role` 값을 권위 있는 정보로 사용.
- 즉, **`role` 이 바뀌면 토큰 재발급 없이 다음 요청부터 즉시 반영**된다.
- `/admin/*` 경로는 모두 `Depends(get_current_admin)` 가 강제되어 있다 — `USER`/`VOLUNTEER` 토큰으로 호출 시 `403 관리자 권한이 필요합니다.`

### 0.3 최초 관리자 부트스트랩

1. 평범하게 회원가입해 `USER` 로 가입한다.
2. 운영자가 SQLAdmin (`http://{host}/admin`) 에 접속해 환경변수 자격(`ADMIN_USERNAME`/`ADMIN_PASSWORD`)으로 로그인.
3. `Users` 테이블에서 해당 행의 `role` 컬럼을 `USER` → `ADMIN` 으로 수정·저장.
4. 그 계정으로 다시 로그인해 받은 access token 으로 `/api/v1/admin/...` 호출 → 통과.

> 관리자 부여 API 는 의도적으로 노출하지 않는다 (무한 권한 상승 방지). 운영자만 접근 가능한 SQLAdmin UI 에서만 가능.

### 0.4 어드민 패널 보호

- SQLAdmin 로그인 실패가 **5회/IP** 누적되면 **15분 잠금** (Redis 카운터). 자격 비교는 `hmac.compare_digest`.
- API JWT 와 SQLAdmin 세션은 서명 키도 분리 (`JWT_SECRET_KEY` vs `ADMIN_SESSION_KEY`).

---

## 1. 봉사자 전환 요청 (`/admin/volunteer-requests`)

### 1.1 요청 목록 조회 — `GET /admin/volunteer-requests` [T1]

**인증 필요 (관리자 권한)**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| status | string | N | `PENDING` | `PENDING` / `APPROVED` / `REJECTED` |
| page | integer | N | 1 | |
| size | integer | N | 20 | 1~100 |

**Response — 200 OK** (`VolunteerRequestListResponse`)
```json
{
  "items": [
    {
      "request_id": 10,
      "user_id": 5,
      "nickname": "댕댕이주인",
      "message": "유기동물 봉사활동 2년 경험이 있습니다. ...",
      "status": "PENDING",
      "submitted_at": "2026-04-15T12:00:00Z",
      "processed_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

**Errors**: 401 / 403(관리자 권한 없음).

---

### 1.2 요청 승인/거부 — `PATCH /admin/volunteer-requests/{request_id}` [T1]

**인증 필요 (관리자 권한)** / **Path**: `request_id`

**Request Body** (`VolunteerRequestActionRequest`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| action | string | Y | `APPROVE` 또는 `REJECT` |
| admin_comment | string | N | (현재는 수신만, 저장 컬럼 없음 — 향후 확장 예정) |

**동작**

- `APPROVE`: 요청 `status` → `APPROVED`, `processed_at` 갱신. 신청자의 `users.role` 이 `USER` 이면 `VOLUNTEER` 로 자동 승급.
- `REJECT`: 요청 `status` → `REJECTED`, `processed_at` 갱신. `users.role` 은 변경되지 않음.
- 이미 처리된 요청(`PENDING` 이 아닌 상태)에 다시 호출하면 409.

**Response — 200 OK** (`VolunteerRequestProcessedResponse`)
```json
{
  "request_id": 10,
  "user_id": 5,
  "status": "APPROVED",
  "processed_at": "2026-04-15T15:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 / 422 | `action` 값 오류 (`APPROVE`/`REJECT` 외) |
| 401 | 인증 실패 |
| 403 | 관리자 권한 없음 |
| 404 | `request_id` 없음 |
| 409 | 이미 처리된 요청 |
