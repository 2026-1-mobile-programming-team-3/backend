# DB 설계 — 시흥가개

DDL은 `schema.sql`, DBML 은 `schema.dbml`, ER 다이어그램은 `er-diagram.md`. 코드(`app/models/*.py`)가 진실 공급원이며 본 문서는 코드 기준으로 동기화한다. API 명세는 `../api-spec/` 참고.

---

## 0. 기술 결정

| 항목 | 결정 | 비고 |
| --- | --- | --- |
| RDBMS | PostgreSQL 16 | `postgis/postgis:16-3.4` 이미지 |
| 공간 데이터 | PostGIS 3.x | 매장/요청 위치 반경 검색 (`geoalchemy2`) |
| 이미지 저장 | 외부 오브젝트 스토리지 (Cloudflare R2 권장) | DB에는 URL만 저장 |
| 인증 토큰 | Refresh Token 화이트리스트 + 디바이스 연결 | 멀티 디바이스 로그인 |
| 비밀번호 | bcrypt / argon2id 해시 | 원문 미저장 |
| 시간 컬럼 | `TIMESTAMPTZ` (UTC) | 클라이언트가 로컬 변환 |
| Soft Delete | `deleted_at TIMESTAMPTZ` | users / stores / matches |
| 명명 규칙 | snake_case, 테이블 복수형, FK는 `{단수명}_id` | |
| 캐시 | Redis 7 — 뉴스(4h)·og:image(24h)·홈 dashboard(5~30m)·rate limit·badge 카운터·WS pub/sub(추후) | |

---

## 1. 테이블 목록

코드 기준 18개. ENUM 11개.

### T0 — MVP (10개)
`users`, `devices`, `refresh_tokens`, `pets`, `notifications`, `notification_settings`, `matches`, `match_applications`, `chat_rooms`, `stores`

### T1 — 안정화 (8개)
`volunteer_requests`, `chat_messages`, `match_reviews`, `store_reviews`, `reports`, `user_blocks`, `store_favorites`, `calendar_events`

> 뉴스 본문 데이터는 네이버 뉴스 검색 API + og:image 스크래핑 결과를 Redis 에 캐시하는 방식이라 별도 DB 테이블 없음. 캘린더만 `calendar_events` 에 저장.

---

## 2. ENUM 타입

| ENUM | 값 |
| --- | --- |
| `user_role` | `USER`, `VOLUNTEER`, `ADMIN` |
| `pet_species` | `DOG`, `CAT`, `OTHER` |
| `pet_gender` | `MALE`, `FEMALE`, `UNKNOWN` |
| `notification_category` | `VOLUNTEER`, `MATCH`, `REVIEW`, `NEWS`, `POLICY`, `SYSTEM` |
| `match_status` | `WAITING`, `MATCHING`, `PROGRESS`, `DONE` |
| `application_status` | `PENDING`, `ACCEPTED`, `REJECTED` |
| `volunteer_request_status` | `PENDING`, `APPROVED`, `REJECTED` |
| `store_category` | `CAFE`, `RESTAURANT`, `PARK` |
| `store_status` | `PENDING`, `APPROVED`, `REJECTED` |
| `report_type` | `USER`, `CHAT` |

> `VolunteerBadgeTier` (`NONE`/`SEED`/`FLOWER`/`FRUIT`/`TREE`) 는 `/users/me/activity-stats` 응답용으로 앱에서 derive — DB 컬럼·enum 으로 존재하지 않는다.

---

## 3. T0 테이블

### 3.1 `users`

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `email` | `VARCHAR(255)` | UNIQUE NOT NULL |
| `password_hash` | `VARCHAR(255)` | NOT NULL |
| `nickname` | `VARCHAR(20)` | UNIQUE NOT NULL |
| `phone` | `VARCHAR(20)` | NULL |
| `role` | `user_role` | NOT NULL DEFAULT `'USER'` |
| `profile_image_url` | `TEXT` | NULL |
| `region_si` | `VARCHAR(50)` | NULL — 거주 시 (예: 시흥시) |
| `region_dong` | `VARCHAR(50)` | NULL — 거주 동 (예: 정왕동) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `deleted_at` | `TIMESTAMPTZ` | NULL — soft delete |

**Index**: `idx_users_role_active` `(role) WHERE deleted_at IS NULL` 부분 인덱스.

> `region_si` / `region_dong` 은 `/geo/reverse` 응답을 클라이언트가 `PATCH /users/me` 로 갱신해 보관하는 값. 홈 대시보드와 봉사 위치 필터 등에서 활용.

### 3.2 `devices`

FCM 토큰. 한 사용자가 여러 기기 가능.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → `users` CASCADE |
| `fcm_token` | `TEXT` | UNIQUE NOT NULL |
| `device_name` | `VARCHAR(100)` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `idx_devices_user_id (user_id)`.

### 3.3 `refresh_tokens`

로그인 세션 화이트리스트. 로그아웃 시 `revoked_at` 기록.

> raw token 대신 SHA-256 해시 저장 — DB 유출 시 세션 도용 차단.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → `users` CASCADE |
| `device_id` | `BIGINT` | FK → `devices` SET NULL |
| `token_hash` | `VARCHAR(64)` | UNIQUE NOT NULL |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL |
| `revoked_at` | `TIMESTAMPTZ` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `idx_refresh_tokens_user_active (user_id) WHERE revoked_at IS NULL`.

### 3.4 `pets`

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → `users` CASCADE |
| `name` | `VARCHAR(50)` | NOT NULL |
| `species` | `pet_species` | NOT NULL |
| `breed` | `VARCHAR(50)` | NULL |
| `age` | `SMALLINT` | NULL, CHECK `ck_pets_age_non_negative`: `age IS NULL OR age >= 0` |
| `weight_kg` | `NUMERIC(5,2)` | NULL, CHECK `ck_pets_weight_positive`: `weight_kg IS NULL OR weight_kg > 0` |
| `is_neutered` | `BOOLEAN` | NOT NULL DEFAULT FALSE |
| `gender` | `pet_gender` | NOT NULL DEFAULT `'UNKNOWN'` |
| `photo_url` | `TEXT` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `idx_pets_user_id (user_id)`.

### 3.5 `notifications`

FCM과 별개로 앱 내 알림 목록·배지 카운트에 사용.

> `is_read` 컬럼 대신 `read_at IS NULL`로 통일 — 두 값 불일치 버그 방지.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → `users` CASCADE |
| `category` | `notification_category` | NOT NULL |
| `title` | `VARCHAR(100)` | NOT NULL |
| `body` | `TEXT` | NOT NULL |
| `link` | `VARCHAR(255)` | NULL — in-app deep link |
| `read_at` | `TIMESTAMPTZ` | NULL — NULL 이면 안 읽음 |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `idx_notifications_user_created (user_id, created_at DESC)`, `idx_notifications_user_unread (user_id, created_at DESC) WHERE read_at IS NULL`.

### 3.6 `notification_settings`

카테고리별 push on/off. 행이 없는 카테고리는 ON(`true`) 으로 간주.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `user_id` | `BIGINT` | PK 일부, FK → `users` CASCADE |
| `category` | `notification_category` | PK 일부 |
| `push_enabled` | `BOOLEAN` | NOT NULL DEFAULT TRUE |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**PK**: `(user_id, category)` 복합. 별도 인덱스 없음 (PK 가 충분).

### 3.7 `matches`

이동 지원 요청 글 + 매칭 진행 상태를 하나의 테이블로 관리.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `author_id` | `BIGINT` | FK → `users` CASCADE |
| `pet_id` | `BIGINT` | FK → `pets` SET NULL |
| `title` | `VARCHAR(100)` | NOT NULL |
| `content` | `TEXT` | NOT NULL |
| `location` | `GEOGRAPHY(POINT, 4326)` | NOT NULL |
| `address` | `VARCHAR(255)` | NULL |
| `desired_date` | `DATE` | NULL |
| `desired_time` | `TIME` | NULL |
| `status` | `match_status` | NOT NULL DEFAULT `'WAITING'` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `deleted_at` | `TIMESTAMPTZ` | NULL — soft delete |

**Index**: `idx_matches_status_created (status, created_at DESC) WHERE deleted_at IS NULL`, `idx_matches_location_gist` GIST(`location`).

### 3.8 `match_applications`

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `match_id` | `BIGINT` | FK → `matches` CASCADE |
| `applicant_id` | `BIGINT` | FK → `users` CASCADE |
| `message` | `TEXT` | NULL |
| `status` | `application_status` | NOT NULL DEFAULT `'PENDING'` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `UNIQUE(match_id, applicant_id)`, 부분 UNIQUE `uniq_match_applications_one_accepted (match_id) WHERE status = 'ACCEPTED'` — 매칭당 ACCEPTED 신청자 1명 보장.

**Index**: `idx_match_applications_match_status (match_id, status)`.

### 3.9 `chat_rooms`

신청 1건 당 채팅방 1개 (작성자 ↔ 신청자 1:1). 첫 메시지 시 자동 생성.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `application_id` | `BIGINT` | NOT NULL UNIQUE, FK → `match_applications` CASCADE |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

### 3.10 `stores`

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `name` | `VARCHAR(100)` | NOT NULL |
| `address` | `VARCHAR(255)` | NOT NULL |
| `phone` | `VARCHAR(20)` | NULL |
| `category` | `store_category` | NOT NULL |
| `location` | `GEOGRAPHY(POINT, 4326)` | NOT NULL |
| `operating_hours` | `VARCHAR(100)` | NULL |
| `photo_urls` | `TEXT[]` | NOT NULL DEFAULT `'{}'` |
| `is_pet_allowed` | `BOOLEAN` | NOT NULL DEFAULT TRUE — 관리자/시드 공식 정보 |
| `status` | `store_status` | NOT NULL DEFAULT `'PENDING'` |
| `created_by` | `BIGINT` | FK → `users` SET NULL |
| `rating_avg` | `NUMERIC(3,2)` | NOT NULL DEFAULT 0 — denormalized |
| `rating_count` | `INTEGER` | NOT NULL DEFAULT 0 — denormalized |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `deleted_at` | `TIMESTAMPTZ` | NULL — soft delete |

**Index**: GIST(`location`) `idx_stores_location_gist`, `idx_stores_status_category (status, category) WHERE deleted_at IS NULL`.

> `rating_avg`/`rating_count`는 `store_reviews` 변동 시 애플리케이션에서 갱신.

---

## 4. T1 테이블

### 4.1 `volunteer_requests`

USER → VOLUNTEER 역할 전환 요청. 관리자 승인 대상.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → `users` CASCADE |
| `message` | `TEXT` | NOT NULL |
| `status` | `volunteer_request_status` | NOT NULL DEFAULT `'PENDING'` |
| `processed_at` | `TIMESTAMPTZ` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: 부분 UNIQUE `uniq_volunteer_requests_one_pending (user_id) WHERE status = 'PENDING'` — PENDING 중복 신청 금지.

**Index**: `idx_volunteer_requests_status_created (status, created_at DESC)`.

### 4.2 `chat_messages`

채팅 메시지. `chat_rooms` 가 신청 단위 1:1 컨테이너를 보장 → `chat_room_id` FK 로만 연결.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `chat_room_id` | `BIGINT` | FK → `chat_rooms` CASCADE |
| `sender_id` | `BIGINT` | FK → `users` SET NULL — 탈퇴 후에도 메시지 유지 |
| `content` | `TEXT` | NOT NULL |
| `read_at` | `TIMESTAMPTZ` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `idx_chat_messages_room_created (chat_room_id, created_at DESC)`.

### 4.3 `match_reviews`

봉사 완료 후 양방향 후기 (작성자→봉사자, 봉사자→작성자).

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `match_id` | `BIGINT` | FK → `matches` CASCADE |
| `reviewer_id` | `BIGINT` | FK → `users` SET NULL |
| `reviewee_id` | `BIGINT` | FK → `users` SET NULL |
| `rating` | `SMALLINT` | NOT NULL CHECK `ck_match_reviews_rating`: `BETWEEN 1 AND 5` |
| `content` | `TEXT` | NULL |
| `proof_image_urls` | `TEXT[]` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `UNIQUE(match_id, reviewer_id)`. CHECK `ck_match_reviews_different_users`: `reviewer_id IS NULL OR reviewee_id IS NULL OR reviewer_id <> reviewee_id`.

**Index**: `idx_match_reviews_reviewee (reviewee_id, created_at DESC)`.

### 4.4 `store_reviews`

> `stores.is_pet_allowed`는 관리자 공식 정보, `store_reviews.is_pet_allowed`는 방문자 현장 확인. 두 출처를 병용.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `store_id` | `BIGINT` | FK → `stores` CASCADE |
| `author_id` | `BIGINT` | FK → `users` SET NULL |
| `rating` | `SMALLINT` | NOT NULL CHECK `ck_store_reviews_rating`: `BETWEEN 1 AND 5` |
| `is_pet_allowed` | `BOOLEAN` | NOT NULL |
| `content` | `TEXT` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `UNIQUE(store_id, author_id)`.

**Index**: `idx_store_reviews_store_created (store_id, created_at DESC)`.

### 4.5 `reports`

사용자 신고 + 채팅 메시지 신고.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `reporter_id` | `BIGINT` | FK → `users` CASCADE |
| `target_user_id` | `BIGINT` | FK → `users` SET NULL |
| `report_type` | `report_type` | NOT NULL DEFAULT `'USER'` |
| `chat_room_id` | `BIGINT` | FK → `chat_rooms` SET NULL |
| `message_id` | `BIGINT` | FK → `chat_messages` SET NULL |
| `reason` | `TEXT` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: CHECK `ck_reports_chat_refs`: `report_type = 'USER' OR (chat_room_id IS NOT NULL AND message_id IS NOT NULL)`. 부분 UNIQUE `ux_reports_user_pair (reporter_id, target_user_id) WHERE report_type = 'USER'` — 사용자 신고 중복 방지(채팅 신고는 메시지 단위라 자유).

**Index**: `idx_reports_target_created (target_user_id, created_at DESC)`.

### 4.6 `user_blocks`

사용자 차단. 양방향 가시성 필터(매칭 리스트/신청자/봉사 위치/채팅)의 진실 공급원.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `blocker_id` | `BIGINT` | NOT NULL FK → `users` CASCADE |
| `blocked_id` | `BIGINT` | NOT NULL FK → `users` CASCADE |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `uq_user_blocks_pair UNIQUE (blocker_id, blocked_id)`. CHECK `ck_user_blocks_no_self`: `blocker_id <> blocked_id`.

**Index**: `idx_user_blocks_blocker (blocker_id, created_at DESC)`.

### 4.7 `store_favorites`

매장 즐겨찾기. 한 사용자 ↔ 한 매장 한 row.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | NOT NULL FK → `users` CASCADE |
| `store_id` | `BIGINT` | NOT NULL FK → `stores` CASCADE |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `uq_store_favorites_pair UNIQUE (user_id, store_id)`.

**Index**: `idx_store_favorites_user_created (user_id, created_at DESC)`.

### 4.8 `calendar_events`

시흥시 반려동물 정책 일정. (뉴스 본문은 별도 테이블 없이 Redis 캐시.)

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `title` | `VARCHAR(200)` | NOT NULL |
| `description` | `TEXT` | NULL |
| `start_date` | `DATE` | NOT NULL |
| `end_date` | `DATE` | NOT NULL, CHECK `ck_calendar_events_dates`: `>= start_date` |
| `event_time` | `TIME` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `idx_calendar_events_dates (start_date, end_date)`.

---

## 5. 관계도

```
users ──┬── pets
        ├── devices ── refresh_tokens
        ├── notifications
        ├── notification_settings
        ├── volunteer_requests
        ├── matches ──┬── match_applications ── chat_rooms ── chat_messages
        │             └── match_reviews
        ├── stores ──┬── store_reviews
        │            └── store_favorites
        ├── reports ── chat_rooms / chat_messages (CHAT 신고)
        └── user_blocks (self N:M)

calendar_events (독립)
```

자세한 ER 다이어그램(Mermaid)은 `er-diagram.md`.

---

## 6. 설계 메모

### 의도적 비정규화
- `stores.rating_avg / rating_count` — 목록 조회 성능. `store_reviews` 변동 시 앱에서 동기화.
- `notifications.title / body` — 발송 시점 메시지 박제. 원본 삭제 후에도 알림 유지.

### FK 삭제 정책
- 기본: `ON DELETE CASCADE` — 부모 삭제 시 자식도 삭제.
- 이력 보존 필요 시: `ON DELETE SET NULL` + nullable — `match_reviews.reviewer_id/reviewee_id`, `store_reviews.author_id`, `chat_messages.sender_id`, `reports.target_user_id/chat_room_id/message_id` 등.

### 부분 인덱스 / 부분 유니크 활용
- `idx_users_role_active WHERE deleted_at IS NULL` — 활성 사용자 역할 조회.
- `idx_notifications_user_unread WHERE read_at IS NULL` — 안 읽음 카운트 빠른 산출.
- `uniq_match_applications_one_accepted WHERE status = 'ACCEPTED'` — 매칭당 ACCEPTED 1명 보장 (동시성 안전).
- `uniq_volunteer_requests_one_pending WHERE status = 'PENDING'` — PENDING 중복 신청 차단.
- `ux_reports_user_pair WHERE report_type = 'USER'` — 사용자 신고 중복 차단, 채팅 신고는 자유.

### 채팅 모델 (chat_rooms 도입)
- 과거 설계는 `chat_messages.application_id` 직접 참조였으나, 현재는 `chat_rooms (application_id UNIQUE)` 중간 테이블 + `chat_messages.chat_room_id` 로 분리.
- 의도: 채팅방 메타데이터(생성 시각, 향후 readers / sticky 등) 확장 여지 + `reports.chat_room_id` 같은 도메인 참조가 메시지가 아닌 방 단위로 묶이게.

### 검토 항목
- [ ] 매장 이름/주소 텍스트 검색 — `pg_trgm` GIN 인덱스 필요 여부
- [ ] 알림 보존 정책 — 90일 이후 일괄 삭제 여부
- [ ] 이메일 대소문자 정규화 — citext 확장 vs 앱 레벨 소문자화
- [ ] `match_reviews.proof_image_urls` 길이 제한 (현재 앱 레벨 10개 cap, DB 레벨 무제한)
