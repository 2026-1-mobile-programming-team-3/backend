# DB 설계 — 시흥가개

DDL은 `schema.sql`, 기능 명세는 `../feature-spec.md`, API 명세는 `../api-spec.md` 참고.

---

## 0. 기술 결정

| 항목 | 결정 | 비고 |
| --- | --- | --- |
| RDBMS | PostgreSQL 16 | Railway Postgres 템플릿 |
| 공간 데이터 | PostGIS 3.x | 매장/요청 위치 반경 검색 |
| 이미지 저장 | 외부 오브젝트 스토리지 (Cloudflare R2 권장) | DB에는 URL만 저장 |
| 인증 토큰 | Refresh Token 화이트리스트 + 디바이스 연결 | 멀티 디바이스 로그인 |
| 비밀번호 | bcrypt / argon2id 해시 | 원문 미저장 |
| 시간 컬럼 | `TIMESTAMPTZ` (UTC) | 클라이언트가 로컬 변환 |
| Soft Delete | `deleted_at TIMESTAMPTZ` | users / stores / matches |
| 명명 규칙 | snake_case, 테이블 복수형, FK는 `{단수명}_id` | |

---

## 1. 테이블 목록

### T0 — MVP (8개)
`users`, `devices`, `refresh_tokens`, `pets`, `notifications`, `matches`, `match_applications`, `stores`

### T1 — 안정화 (6개)
`volunteer_requests`, `chat_messages`, `match_reviews`, `store_reviews`, `reports`, `calendar_events`

---

## 2. ENUM 타입

| ENUM | 값 |
| --- | --- |
| `user_role` | `USER`, `VOLUNTEER`, `ADMIN` |
| `pet_species` | `DOG`, `CAT`, `OTHER` |
| `notification_category` | `VOLUNTEER`, `MATCH`, `REVIEW`, `NEWS`, `POLICY`, `SYSTEM` |
| `match_status` | `WAITING`, `MATCHING`, `PROGRESS`, `DONE` |
| `application_status` | `PENDING`, `ACCEPTED`, `REJECTED` |
| `volunteer_request_status` | `PENDING`, `APPROVED`, `REJECTED` |
| `store_category` | `CAFE`, `RESTAURANT`, `PARK` |
| `store_status` | `PENDING`, `APPROVED`, `REJECTED` |

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
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `deleted_at` | `TIMESTAMPTZ` | NULL — soft delete |

**Index**: `(role) WHERE deleted_at IS NULL` 부분 인덱스.

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

**Index**: `(user_id)`.

### 3.3 `refresh_tokens`

로그인 세션 화이트리스트. 로그아웃 시 `revoked_at` 기록.

> raw token 대신 SHA-256 해시 저장 — DB 유출 시 세션 도용 차단.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → `users` CASCADE |
| `device_id` | `BIGINT` | FK → `devices` SET NULL, NULL 허용 |
| `token_hash` | `VARCHAR(64)` | UNIQUE NOT NULL |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL |
| `revoked_at` | `TIMESTAMPTZ` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `(user_id) WHERE revoked_at IS NULL` 부분 인덱스.

### 3.4 `pets`

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → `users` CASCADE |
| `name` | `VARCHAR(50)` | NOT NULL |
| `species` | `pet_species` | NOT NULL |
| `breed` | `VARCHAR(50)` | NULL |
| `age` | `SMALLINT` | NULL, CHECK `age IS NULL OR age >= 0` (`ck_pets_age_non_negative`) |
| `weight_kg` | `NUMERIC(5,2)` | NULL, CHECK `weight_kg IS NULL OR weight_kg > 0` (`ck_pets_weight_positive`) |
| `is_neutered` | `BOOLEAN` | NOT NULL DEFAULT FALSE |
| `photo_url` | `TEXT` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `(user_id)`.

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
| `read_at` | `TIMESTAMPTZ` | NULL — NULL이면 안 읽음 |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `(user_id, created_at DESC)`, `(user_id, created_at DESC) WHERE read_at IS NULL`.

### 3.6 `matches`

이동 지원 요청 글 + 매칭 진행 상태를 하나의 테이블로 관리.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `author_id` | `BIGINT` | FK → `users` CASCADE |
| `pet_id` | `BIGINT` | FK → `pets` SET NULL, NULL 허용 |
| `title` | `VARCHAR(100)` | NOT NULL |
| `content` | `TEXT` | NOT NULL |
| `location` | `GEOGRAPHY(POINT, 4326)` | NOT NULL |
| `address` | `VARCHAR(255)` | NULL |
| `desired_date` | `DATE` | NULL |
| `status` | `match_status` | NOT NULL DEFAULT `'WAITING'` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `deleted_at` | `TIMESTAMPTZ` | NULL — soft delete |

**Index**: `(status, created_at DESC) WHERE deleted_at IS NULL`, GIST(`location`).

### 3.7 `match_applications`

봉사자가 요청 글에 신청. 한 매칭에 여러 신청자, 수락은 1명만.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `match_id` | `BIGINT` | FK → `matches` CASCADE |
| `applicant_id` | `BIGINT` | FK → `users` CASCADE |
| `message` | `TEXT` | NULL |
| `status` | `application_status` | NOT NULL DEFAULT `'PENDING'` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `UNIQUE(match_id, applicant_id)`, 부분 UNIQUE `(match_id) WHERE status = 'ACCEPTED'`.

### 3.8 `stores`

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
| `created_by` | `BIGINT` | FK → `users` SET NULL, NULL 허용 |
| `rating_avg` | `NUMERIC(3,2)` | NOT NULL DEFAULT 0 — denormalized |
| `rating_count` | `INTEGER` | NOT NULL DEFAULT 0 — denormalized |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `deleted_at` | `TIMESTAMPTZ` | NULL — soft delete |

**Index**: GIST(`location`), `(status, category) WHERE deleted_at IS NULL`.

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

**Constraint**: 부분 UNIQUE `(user_id) WHERE status = 'PENDING'` — PENDING 중복 신청 금지.

### 4.2 `chat_messages`

채팅 스레드 단위 = `match_applications` 1건 (작성자 ↔ 신청자 1:1).

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `application_id` | `BIGINT` | FK → `match_applications` CASCADE |
| `sender_id` | `BIGINT` | FK → `users` SET NULL, NULL 허용 |
| `content` | `TEXT` | NOT NULL |
| `read_at` | `TIMESTAMPTZ` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `(application_id, created_at DESC)`.

### 4.3 `match_reviews`

봉사 완료 후 양방향 후기 (작성자→봉사자, 봉사자→작성자).

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `match_id` | `BIGINT` | FK → `matches` CASCADE |
| `reviewer_id` | `BIGINT` | FK → `users` SET NULL, NULL 허용 |
| `reviewee_id` | `BIGINT` | FK → `users` SET NULL, NULL 허용 |
| `rating` | `SMALLINT` | NOT NULL CHECK `BETWEEN 1 AND 5` |
| `content` | `TEXT` | NULL |
| `proof_image_urls` | `TEXT[]` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `UNIQUE(match_id, reviewer_id)`.

**Index**: `(reviewee_id, created_at DESC)`.

### 4.4 `store_reviews`

> `stores.is_pet_allowed`는 관리자 공식 정보, `store_reviews.is_pet_allowed`는 방문자 현장 확인. 두 출처를 병용.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `store_id` | `BIGINT` | FK → `stores` CASCADE |
| `author_id` | `BIGINT` | FK → `users` SET NULL, NULL 허용 |
| `rating` | `SMALLINT` | NOT NULL CHECK `BETWEEN 1 AND 5` |
| `is_pet_allowed` | `BOOLEAN` | NOT NULL |
| `content` | `TEXT` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `UNIQUE(store_id, author_id)`.

**Index**: `(store_id, created_at DESC)`.

### 4.5 `reports`

신고자/대상자/사유만 기록하는 단순 로그.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `reporter_id` | `BIGINT` | FK → `users` CASCADE |
| `target_user_id` | `BIGINT` | FK → `users` SET NULL, NULL 허용 |
| `reason` | `TEXT` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Constraint**: `UNIQUE(reporter_id, target_user_id)`.

**Index**: `(target_user_id, created_at DESC)`.

### 4.6 `calendar_events`

시흥시 반려동물 정책 일정.

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | PK |
| `title` | `VARCHAR(200)` | NOT NULL |
| `description` | `TEXT` | NULL |
| `start_date` | `DATE` | NOT NULL |
| `end_date` | `DATE` | NOT NULL, CHECK `>= start_date` |
| `event_time` | `TIME` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT NOW() |

**Index**: `(start_date, end_date)`.

---

## 5. 관계도

```
users ──┬── pets
        ├── devices ── refresh_tokens
        ├── notifications
        ├── volunteer_requests
        ├── matches ──┬── match_applications ── chat_messages
        │             └── match_reviews
        ├── stores ── store_reviews
        └── reports

calendar_events (독립)
```

---

## 6. 설계 메모

### 의도적 비정규화
- `stores.rating_avg / rating_count` — 목록 조회 성능. `store_reviews` 변동 시 앱에서 동기화.
- `notifications.title / body` — 발송 시점 메시지 박제. 원본 삭제 후에도 알림 유지.

### FK 삭제 정책
- 기본: `ON DELETE CASCADE` — 부모 삭제 시 자식도 삭제.
- 이력 보존 필요 시: `ON DELETE SET NULL` + nullable — `match_reviews`, `store_reviews`, `chat_messages` 등.

### 검토 항목
- [ ] 매장 이름/주소 텍스트 검색 — `pg_trgm` GIN 인덱스 필요 여부
- [ ] 알림 보존 정책 — 90일 이후 일괄 삭제 여부
- [ ] 이메일 대소문자 정규화 — citext 확장 vs 앱 레벨 소문자화

---

