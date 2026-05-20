# API 명세서 — 사용자(My) (`/users/me`)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/users.py` (prefix `/users`, tag `users`).

> 본 문서는 `users.py` 라우터 11개 엔드포인트를 다룬다. 펫 CRUD는 `pets.md`, 즐겨찾기는 `favorites.md`, 차단은 `blocks.md`, 봉사자 전환 승인은 `admin.md` 별도 문서.

---

## 1. 내 정보

### 1.1 내 정보 조회 — `GET /users/me` [T0]

**인증 필요**

**Response — 200 OK** (`UserMeResponse`)
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "댕댕이주인",
  "phone": "010-1234-5678",
  "role": "USER",
  "profile_image_url": null,
  "region_si": "시흥시",
  "region_dong": "정왕동",
  "pets": [
    {
      "id": 1,
      "name": "초코",
      "species": "DOG",
      "breed": "말티즈",
      "age": 3,
      "gender": "MALE",
      "is_neutered": false,
      "note": "닭고기 알레르기 있음."
    }
  ],
  "created_at": "2026-04-15T12:00:00Z"
}
```

> **대표 펫**: 마이페이지의 "대표 펫 1마리" 카드는 `pets[0]` (가장 먼저 등록된 펫) 사용. 별도 지정 API 없음.

**Errors**: 401.

---

### 1.2 계정 정보 수정 — `PATCH /users/me` [T0]

**인증 필요**

**Request Body** (변경할 필드만 전송 — 모두 옵셔널)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| nickname | string | 2~20자, trim 후 검증 |
| phone | string | `^\+?[0-9\-\s]{9,20}$` (공통 정책 §0.7) |
| profile_image_url | string | 프로필 이미지 URL |
| region_si | string \| null | 거주 시. `null` 전송 시 미설정으로 초기화 |
| region_dong | string \| null | 거주 동 |

**Response — 200 OK** (`UserResponse`)
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "새닉네임",
  "phone": "010-9999-8888",
  "role": "USER",
  "profile_image_url": "https://storage.example.com/profiles/1.jpg",
  "region_si": "시흥시",
  "region_dong": "정왕동",
  "created_at": "2026-04-15T12:00:00Z",
  "updated_at": "2026-04-15T13:00:00Z"
}
```

**Errors**: 400 / 401 / 409(닉네임 중복).

---

### 1.3 비밀번호 변경 — `PUT /users/me/password` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| current_password | string | Y | 현재 비밀번호 |
| new_password | string | Y | 새 비밀번호 — 정책은 `auth.md` §0.7 |

> **부수 효과**: 성공 시 해당 사용자의 모든 활성 refresh token 일괄 revoke → 다른 디바이스/세션은 다음 호출에서 401.

**Response — 200 OK**
```json
{ "message": "비밀번호가 변경되었습니다." }
```

**Errors**: 400(새 비밀번호 정책 미충족) / 401(현재 비밀번호 불일치).

---

### 1.4 계정 탈퇴 — `DELETE /users/me` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| password | string | Y | 비밀번호 재확인 |
| reason | string | N | 탈퇴 사유 (최대 500자) |

> **부수 효과**: soft delete(`deleted_at = NOW()`) + 모든 활성 refresh token 일괄 revoke.

**Response — 200 OK**
```json
{ "message": "계정이 비활성화되었습니다. 30일 후 영구 삭제됩니다." }
```

**Errors**: 401.

---

## 2. 봉사자 권한

### 2.1 봉사자 역할 전환 신청 — `POST /users/me/volunteer-request` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| message | string | Y | 자기소개·지원 동기·봉사 경험 등 (1~2000자) |

**Response — 201 Created** (`VolunteerRequestResponse`)
```json
{
  "id": 10,
  "user_id": 5,
  "message": "유기동물 봉사활동 2년 경험이 있습니다. ...",
  "status": "PENDING",
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 |
| 401 | 인증 실패 |
| 409 | 이미 봉사자/관리자이거나 대기 중(`PENDING`) 요청이 존재 |

> 관리자 승인 흐름은 `admin.md` 참고. `APPROVE` 시 `users.role` → `VOLUNTEER` 자동 승급, 토큰 재발급 불필요(다음 요청부터 반영).

---

### 2.2 봉사자 누적 통계 — `GET /users/me/volunteer-stats` [T2]

**인증 필요 (봉사자 권한 — `VOLUNTEER` 또는 `ADMIN`)**

본인이 ACCEPTED 봉사자로 참여하고 매칭이 `DONE` 인 건수와, `match_reviews.reviewee_id = me` 후기의 평점 평균을 반환.

**Response — 200 OK** (`VolunteerStatsResponse`)
```json
{
  "total_count": 3,
  "total_hours": 0.0,
  "avg_rating": 4.7
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| total_count | integer | 완료(DONE) 매칭에 ACCEPTED로 참여한 건수 |
| total_hours | float | 누적 봉사 시간. ⚠️ 시간 추적 컬럼이 아직 없어 현재 항상 `0.0`. 추후 활동 로그 추가 시 보강 예정. |
| avg_rating | float \| null | reviewee 후기 평점 평균. 후기가 한 건도 없으면 `null`. |

**Errors**: 401 / 403(봉사자 권한 없음).

---

## 3. 매칭 / 활동

### 3.1 내 매칭 목록 조회 — `GET /users/me/matches` [T0]

**인증 필요**

마이페이지 "내가 작성한 요청 / 내가 신청한 봉사" 카드 데이터원.

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| role | string | Y | - | `author` (본인 작성) 또는 `applicant` (본인 신청) |
| status | string | N | - | `WAITING` / `MATCHING` / `PROGRESS` / `DONE` |
| page | integer | N | 1 | |
| size | integer | N | 20 | 1~100 |

**Response — 200 OK** (`MyMatchListResponse`)

`match.md` §3.4 의 매칭 리스트 항목에 다음 enrichment 추가:

| 필드 | role | 설명 |
| --- | --- | --- |
| applications_count | author | 현 신청자 총 수 (applicant 시 `null`) |
| matched_applicant_nickname | author | ACCEPTED 봉사자 닉네임. 없으면 `null` |
| unread_message_count | author | 작성자 시점 미읽음 메시지 합산 |
| my_application_status | applicant | `PENDING` / `ACCEPTED` / `REJECTED` |
| received_rating | applicant | 본인이 reviewee로 받은 평점(1~5). 없으면 `null` |

```json
{
  "items": [
    {
      "match_id": 1,
      "title": "...",
      "address": "...",
      "latitude": 37.34,
      "longitude": 126.73,
      "desired_date": "2026-05-10",
      "desired_time": "10:00",
      "status": "WAITING",
      "author_nickname": "...",
      "created_at": "...",
      "my_application_status": "PENDING",
      "applications_count": null,
      "matched_applicant_nickname": null,
      "unread_message_count": 0,
      "received_rating": null
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

**Errors**: 401 / 422(role 누락·잘못된 값).

---

### 3.2 활동 통계 + 봉사 뱃지 — `GET /users/me/activity-stats` [T1]

**인증 필요**

마이페이지의 활동 통계 카드(내 요청 수·봉사 참여 수·즐겨찾기 수) + 봉사 뱃지 등급/진행률을 1회 호출로 반환.

**Response — 200 OK** (`ActivityStatsResponse`)
```json
{
  "my_match_count": 3,
  "volunteer_completed_count": 2,
  "favorite_count": 5,
  "badge": {
    "tier": "SEED",
    "count": 2,
    "next_tier": "FLOWER",
    "next_threshold": 3,
    "progress_pct": 50
  }
}
```

- `my_match_count`: 본인이 작성한 매칭 중 `deleted_at IS NULL` 총 건수 (상태 무관).
- `volunteer_completed_count`: 본인이 ACCEPTED 봉사자였고 매칭이 `DONE` 인 건수.
- `favorite_count`: 본인 즐겨찾기 중 매장이 `APPROVED` 이고 살아있는 것의 수.
- `badge.tier` enum: `NONE` / `SEED` / `FLOWER` / `FRUIT` / `TREE`. 임계값 1·3·8·15.
- `badge.progress_pct`: 현 등급 시작 ~ 다음 등급 임계 사이 진행률(0~100). 최고 등급(`TREE`)이면 100.

**Errors**: 401.

---

## 4. 알림 설정

### 4.1 알림 설정 조회 — `GET /users/me/notification-settings` [T1]

**인증 필요**

카테고리별 push on/off 상태. 행이 없는 카테고리는 기본 `true` 로 응답.

**Response — 200 OK** (`NotificationSettingsResponse`)
```json
{
  "settings": {
    "VOLUNTEER": true,
    "MATCH": true,
    "REVIEW": false,
    "NEWS": true,
    "POLICY": true,
    "SYSTEM": true
  }
}
```

---

### 4.2 알림 설정 변경 — `PUT /users/me/notification-settings` [T1]

**인증 필요**

**Request Body** (포함된 카테고리만 갱신 — upsert)
```json
{
  "settings": {
    "REVIEW": false
  }
}
```

**Response — 200 OK** — 4.1과 동일 (전체 카테고리 현 상태).

> 카테고리 enum 은 `VOLUNTEER` / `MATCH` / `REVIEW` / `NEWS` / `POLICY` / `SYSTEM`. `notification.md` 참고.
