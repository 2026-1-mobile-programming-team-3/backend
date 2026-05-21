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

---

## 2. 매장 추가/수정 요청 (`/admin/store-requests`)

사용자가 `POST /maps/store-requests` 로 제출한 매장 추가(`ADD`) / 수정(`UPDATE`) 요청을 관리자가 검수·승인하는 라우트. 사용자 측 API 는 `map.md §5.13` 참고.

### 2.1 요청 목록 조회 — `GET /admin/store-requests` [T1]

**인증 필요 (관리자 권한)**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| status | string | N | `PENDING` | `PENDING` / `APPROVED` / `REJECTED` |
| page | integer | N | 1 | |
| size | integer | N | 20 | 1~100 |

**Response — 200 OK** (`StoreRequestAdminListResponse`)
```json
{
  "items": [
    {
      "request_id": 7,
      "user_id": 21,
      "nickname": "배곧호텔주인",
      "type": "ADD",
      "target_store_id": null,
      "payload": {
        "name": "배곧 펫호텔",
        "address": "경기도 시흥시 배곧동 ...",
        "category": "PET_HOTEL",
        "is_pet_allowed": true,
        "latitude": 37.3752,
        "longitude": 126.7281,
        "phone": "031-000-0000",
        "operating_hours": "00:00-24:00",
        "photo_urls": ["https://..."] ,
        "plans": [
          {"plan_name": "1박 소형견", "price_krw": 40000, "display_order": 0},
          {"plan_name": "1박 중형견", "price_krw": 55000, "display_order": 1}
        ]
      },
      "proof_urls": ["https://private-bucket/.../biz-license.pdf"],
      "message": "본인이 운영하는 매장입니다.",
      "status": "PENDING",
      "reviewer_id": null,
      "review_note": null,
      "processed_at": null,
      "created_at": "2026-05-21T09:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

> `proof_urls` 는 신청자가 외부 비공개 스토리지에 올린 사업자등록증 등 증빙 자료 URL(검토용). 클라이언트가 서명 URL 관리 책임을 가진다.
> `payload.plans` 는 카테고리가 `PET_HOTEL` 일 때만 의미. 다른 카테고리에서 plans 가 들어 있으면 422로 거부됨 (서비스 레이어).

**Errors**: 401 / 403.

---

### 2.2 요청 상세 조회 — `GET /admin/store-requests/{request_id}` [T1]

**인증 필요 (관리자 권한)** / **Path**: `request_id`

목록 응답의 `items[i]` 와 동일한 단일 객체를 반환 (`StoreRequestAdminItem`). `payload` 와 `proof_urls` 전체를 그대로 노출하므로, 어드민 UI에서 diff 비교 시 `target_store_id` 가 있으면 `/maps/stores/{target_store_id}` 와 좌우 비교.

**Errors**: 401 / 403 / 404.

---

### 2.3 요청 승인/거부 — `PATCH /admin/store-requests/{request_id}` [T1]

**인증 필요 (관리자 권한)** / **Path**: `request_id`

**Request Body** (`StoreRequestActionRequest`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| action | string | Y | `APPROVE` 또는 `REJECT` |
| note | string | N | 반려 사유·관리자 메모 (최대 1000자). 신청자에게 알림 본문으로도 전달됨. |

**동작 — `APPROVE`**

단일 트랜잭션 안에서:

1. `type=ADD` → `stores` 테이블에 신규 행 INSERT (`status=APPROVED`, `owner_user_id` 와 `created_by` 모두 신청자 id 로). 카테고리가 `PET_HOTEL` 이고 `payload.plans` 가 있으면 `store_pricing_plans` 도 같이 INSERT.
2. `type=UPDATE` → `target_store_id` 매장의 변경 필드만 갱신. lat/lng 둘 다 있으면 `location` 도 갱신. `payload.plans` 가 있으면 해당 매장의 plans 를 replace-all (기존 모두 삭제 후 새로 INSERT). 카테고리가 `PET_HOTEL` 에서 다른 값으로 변경된 경우 기존 plans 일괄 삭제.
3. `store_requests`: `status=APPROVED`, `processed_at=NOW()`, `reviewer_id=관리자 id`, `review_note=note`.
4. 신청자에게 `SYSTEM` 카테고리 알림 enqueue (FCM 푸시 활성화 시 자동 발송).

**동작 — `REJECT`**

`store_requests` 상태만 `REJECTED` 로 변경. `stores`/`store_pricing_plans` 변경 없음. 신청자에게 알림(반려 사유=`note`).

**제약**

- 이미 처리된 요청(`PENDING` 이 아닌 상태)에 다시 호출 → 409.
- UPDATE 승인 시점에 대상 매장이 이미 삭제됐으면 → 404.
- 카테고리 != `PET_HOTEL` 인데 `payload.plans` 가 들어 있으면 → 422 (방어 검증, 정상 흐름에서는 제출 시점에 이미 차단됨).

**Response — 200 OK** (`StoreRequestProcessedResponse`)
```json
{
  "request_id": 7,
  "type": "ADD",
  "target_store_id": null,
  "status": "APPROVED",
  "processed_at": "2026-05-21T10:30:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 / 422 | `action` 값 오류, 또는 plans/카테고리 불일치 |
| 401 | 인증 실패 |
| 403 | 관리자 권한 없음 |
| 404 | `request_id` 없음, 또는 UPDATE 대상 매장이 사라짐 |
| 409 | 이미 처리된 요청 |
