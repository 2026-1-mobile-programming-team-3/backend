# API 명세서 — 시흥가개

본 문서는 시흥가개 백엔드 REST API의 전체 엔드포인트 명세이다.
기능 요구사항은 `기능명세서.md`, 프로젝트 전반 정보는 `프로젝트정보.md` 참고.

## 0. 공통 사항

### 0.1 Base URL
```
https://{host}/api/v1
```

### 0.2 공통 헤더

| 헤더 | 값 | 필수 | 비고 |
| --- | --- | --- | --- |
| Content-Type | application/json | 요청 본문이 있는 경우 Y | |
| Authorization | `Bearer {access_token}` | 인증 필요 API에서 Y | JWT |

### 0.3 인증

- JWT 기반.
- 로그인 시 `access_token`(30분), `refresh_token`(7일) 발급.
- Access Token 만료 시 `/auth/refresh`로 갱신.

### 0.4 공통 에러 코드

| 상태 코드 | 의미 |
| --- | --- |
| 400 | 요청 본문/파라미터 유효성 검증 실패 |
| 401 | 인증 실패 (토큰 미제공/만료/무효) |
| 403 | 권한 없음 (역할 부족, 본인 소유 아님) |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복 등록, 이미 처리됨 등) |
| 500 | 서버 내부 오류 |

### 0.5 공통 응답 컨벤션

- 성공 응답은 도메인별 JSON 객체.
- 페이지네이션: `{ "items": [...], "total": N, "page": N, "size": N }`.
- 시각: ISO-8601 (`2026-04-15T12:00:00Z`).
- 날짜: `YYYY-MM-DD`.

### 0.6 우선순위/난이도 표기 약어
- 우선순위: T0 (필수) / T1 (부가) / T2 (확장)
- 난이도: 하 / 중 / 상

---

## 1. 사용자 관리 (Auth)

### 1.1 회원가입 — `POST /auth/signup` [T0]

**Request Headers**

| 헤더 | 값 | 필수 |
| --- | --- | --- |
| Content-Type | application/json | Y |

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 이메일 (로그인 ID) |
| password | string | Y | 비밀번호 (8자 이상, 영문+숫자+특수문자) |
| nickname | string | Y | 닉네임 (2~20자) |
| phone | string | N | 연락처 |

```json
{
  "email": "user@example.com",
  "password": "securePassword123!",
  "nickname": "댕댕이주인",
  "phone": "010-1234-5678"
}
```

**Response — 201 Created**
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "댕댕이주인",
  "role": "USER",
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 (비밀번호 조건 미충족 등) |
| 409 | 이미 등록된 이메일 |

---

### 1.2 로그인 — `POST /auth/login` [T0]

**Request Body**

| 필드 | 타입 | 필수 |
| --- | --- | --- |
| email | string | Y |
| password | string | Y |

```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Response — 200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 이메일 또는 비밀번호 불일치 |

---

### 1.3 토큰 갱신 — `POST /auth/refresh` [T0]

**Request Body**

| 필드 | 타입 | 필수 |
| --- | --- | --- |
| refresh_token | string | Y |

```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIs..." }
```

**Response — 200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | refresh token 만료 또는 무효 |

---

### 1.4 로그아웃 — `POST /auth/logout` [T0]

**인증 필요** (Authorization 헤더)

**Request Body**
```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIs..." }
```

**Response — 200 OK**
```json
{ "message": "로그아웃되었습니다." }
```

---

### 1.5 내 정보 조회 — `GET /users/me` [T0]

**인증 필요**

**Response — 200 OK**
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "댕댕이주인",
  "phone": "010-1234-5678",
  "role": "USER",
  "profile_image_url": null,
  "pets": [
    {
      "id": 1,
      "name": "초코",
      "species": "DOG",
      "breed": "말티즈",
      "is_neutered": false
    }
  ],
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |

---

### 1.6 계정 정보 수정 — `PATCH /users/me` [T0]

**인증 필요**

**Request Body** (변경할 필드만 전송)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| nickname | string | N | 변경할 닉네임 |
| phone | string | N | 변경할 연락처 |
| profile_image_url | string | N | 프로필 이미지 URL |

**Response — 200 OK**
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "새닉네임",
  "phone": "010-9999-8888",
  "profile_image_url": "https://storage.example.com/profiles/1.jpg",
  "role": "USER",
  "updated_at": "2026-04-15T13:00:00Z"
}
```

---

### 1.7 비밀번호 변경 — `PUT /users/me/password` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| current_password | string | Y | 현재 비밀번호 |
| new_password | string | Y | 새 비밀번호 |

**Response — 200 OK**
```json
{ "message": "비밀번호가 변경되었습니다." }
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 새 비밀번호 유효성 실패 |
| 401 | 현재 비밀번호 불일치 |

---

### 1.8 계정 탈퇴 — `DELETE /users/me` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| password | string | Y | 비밀번호 재확인 |
| reason | string | N | 탈퇴 사유 |

**Response — 200 OK**
```json
{ "message": "계정이 비활성화되었습니다. 30일 후 영구 삭제됩니다." }
```

---

### 1.9 반려동물 등록 — `POST /users/me/pets` [T0]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 반려동물 이름 |
| species | string | Y | `DOG`, `CAT`, `OTHER` |
| breed | string | N | 품종 |
| age | integer | N | 나이 |
| weight_kg | float | N | 체중 (kg) |
| is_neutered | boolean | Y | 중성화 여부 |
| photo_url | string | N | 사진 URL |

**Response — 201 Created**
```json
{
  "id": 1,
  "name": "초코",
  "species": "DOG",
  "breed": "말티즈",
  "age": 3,
  "weight_kg": 4.2,
  "is_neutered": false,
  "photo_url": "https://storage.example.com/pets/choco.jpg",
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 |
| 401 | 인증 실패 |

---

### 1.10 반려동물 수정 — `PATCH /users/me/pets/{pet_id}` [T1]

**인증 필요** / **Path**: `pet_id` (integer)

**Request Body** (변경할 필드만 전송)

| 필드 | 타입 | 필수 |
| --- | --- | --- |
| is_neutered | boolean | N |
| weight_kg | float | N |

**Response — 200 OK**
```json
{
  "id": 1,
  "name": "초코",
  "species": "DOG",
  "breed": "말티즈",
  "age": 3,
  "weight_kg": 4.5,
  "is_neutered": true,
  "photo_url": "https://storage.example.com/pets/choco.jpg",
  "updated_at": "2026-04-15T14:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 |
| 401 | 인증 실패 |
| 403 | 본인의 반려동물이 아님 |
| 404 | pet_id 없음 |

---

### 1.11 반려동물 삭제 — `DELETE /users/me/pets/{pet_id}` [T1]

**인증 필요** / **Path**: `pet_id` (integer)

**Response — 204 No Content** (응답 본문 없음)

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 본인의 반려동물이 아님 |
| 404 | pet_id 없음 |

---

### 1.12 봉사자 역할 전환 요청 — `POST /users/me/volunteer-request` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| introduction | string | Y | 자기소개 (50자 이상) |
| experience | string | N | 봉사 경험 |
| has_vehicle | boolean | Y | 차량 보유 여부 |

**Response — 201 Created**
```json
{
  "request_id": 10,
  "status": "PENDING",
  "submitted_at": "2026-04-15T12:00:00Z",
  "message": "봉사자 신청이 접수되었습니다. 관리자 승인을 기다려 주세요."
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 (자기소개 50자 미만) |
| 401 | 인증 실패 |
| 409 | 이미 봉사자이거나 대기 중 요청 존재 |

---

### 1.13 (관리자) 봉사자 요청 목록 조회 — `GET /admin/volunteer-requests` [T1]

**인증 필요 (관리자 권한)**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| status | string | N | PENDING | `PENDING` / `APPROVED` / `REJECTED` |
| page | integer | N | 1 | 페이지 |
| size | integer | N | 20 | 페이지 크기 |

**Response — 200 OK**
```json
{
  "items": [
    {
      "request_id": 10,
      "user_id": 5,
      "nickname": "댕댕이주인",
      "introduction": "유기동물 봉사활동 2년 경험이 있습니다.",
      "experience": "시흥시 유기동물보호센터 자원봉사 참여",
      "has_vehicle": true,
      "status": "PENDING",
      "submitted_at": "2026-04-15T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 관리자 권한 없음 |

---

### 1.14 (관리자) 봉사자 요청 승인/거부 — `PATCH /admin/volunteer-requests/{request_id}` [T1]

**인증 필요 (관리자 권한)** / **Path**: `request_id` (integer)

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| action | string | Y | `APPROVE` 또는 `REJECT` |
| admin_comment | string | N | 관리자 코멘트 |

**Response — 200 OK**
```json
{
  "request_id": 10,
  "user_id": 5,
  "status": "APPROVED",
  "admin_comment": "승인합니다. 활동을 시작해 주세요.",
  "processed_at": "2026-04-15T15:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | action 값 오류 |
| 401 | 인증 실패 |
| 403 | 관리자 권한 없음 |
| 404 | request_id 없음 |
| 409 | 이미 처리된 요청 |

---

## 2. 알림 (Notification)

### 2.1 알림 목록 조회 — `GET /notifications` [T0]

**인증 필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| is_read | boolean | N | - | `true`: 읽은 알림만, `false`: 안읽은 알림만 |
| category | string | N | - | `VOLUNTEER` / `MATCH` / `REVIEW` / `NEWS` / `POLICY` / `SYSTEM` |
| page | integer | N | 1 | |
| size | integer | N | 20 | |

**Response — 200 OK**
```json
{
  "items": [
    {
      "id": 101,
      "category": "MATCH",
      "title": "매칭 상태 변경",
      "body": "요청하신 중성화 이동 지원이 수락되었습니다.",
      "is_read": false,
      "link": "/match/42",
      "created_at": "2026-04-15T14:30:00Z"
    }
  ],
  "total": 2,
  "unread_count": 1,
  "page": 1,
  "size": 20
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 잘못된 query parameter |
| 401 | 인증 실패 |

---

### 2.2 알림 전체 읽음 처리 — `PATCH /notifications/read-all` [T1]

**인증 필요**

**Response — 200 OK**
```json
{
  "updated_count": 5,
  "message": "5건의 알림을 읽음 처리했습니다."
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |

---

### 2.3 읽지 않은 알림 개수 조회 — `GET /notifications/unread-count` [T0]

**인증 필요**

**Response — 200 OK**
```json
{ "unread_count": 3 }
```

---

### 2.4 푸시 알림 디바이스 토큰 등록 — `POST /notifications/devices` [T0]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| fcm_token | string | Y | FCM 디바이스 토큰 |
| device_name | string | N | 기기명 (디버깅용) |

**Response — 201 Created**
```json
{
  "id": 1,
  "registered_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 409 | 이미 등록된 토큰 (무시 가능) |

---

## 3. 중성화 이동 지원 매칭 (Match)

> ⚠️ 본 카테고리는 원본 명세에서 API 상세 정의가 누락되어 있어, 아래는 **제안 명세 (TBD)** 이며 담당자 확정 후 갱신 예정.

### 3.1 이동 지원 요청 글 작성 — `POST /matches` [T0]
- 인증 필요
- Body(예정): `title`, `content`, `latitude`, `longitude`, `desired_date`, `pet_id`
- Response: 201 Created + 생성된 요청 정보

### 3.2 이동 지원 요청 글 수정 — `PATCH /matches/{match_id}` [T1]
- 인증 필요 / 본인 작성 글만 수정 가능
- Errors: 403 (본인 아님), 404 (없음), 409 (이미 매칭 진행 중)

### 3.3 이동 지원 요청 글 삭제 — `DELETE /matches/{match_id}` [T1]
- 인증 필요 / 본인 작성 글만 삭제 가능 / Response: 204

### 3.4 이동 지원 요청 목록 조회 — `GET /matches` [T0]
- 인증 필요 (봉사자 권한 권장)
- Query(예정): `status`, `region`, `from_date`, `to_date`, `page`, `size`

### 3.5 특정 요청 상세 정보 조회 — `GET /matches/{match_id}` [T0]
- 인증 필요 / Path: `match_id`

### 3.6 봉사 신청하기 — `POST /matches/{match_id}/applications` [T0]
- 인증 필요 (봉사자) / Body(예정): `message`
- Response: 201 + 신청 정보

### 3.7 신청자 목록 조회(작성자용) — `GET /matches/{match_id}/applications` [T0]
- 인증 필요 (요청 작성자만)
- Errors: 403 (작성자 아님)

### 3.8 봉사자 매칭 수락/거절 — `PATCH /matches/{match_id}/applications/{application_id}` [T0]
- 인증 필요 (요청 작성자만)
- Body(예정): `action` (`ACCEPT` / `REJECT`)
- 호출 위치: 신청자 카드의 "거절" 버튼 또는 채팅방 안의 "이 분과 매칭하기" 액션
- 동작: 작성자가 채팅으로 대화 후 결정. `ACCEPT` 시 같은 매칭의 다른 PENDING application은 모두 자동 `REJECTED` 처리되고 `matches.status = 'PROGRESS'`로 전이. 거절된 application의 채팅 스레드는 비활성화(메시지는 보존).
- Response: 매칭 상태 변경 + 양측 알림 발송

### 3.9 매칭 상태 실시간 업데이트 — `PATCH /matches/{match_id}/status` [T1]
- 인증 필요
- Body(예정): `status` (`PROGRESS` / `DONE`)
- WebSocket 채널 `/ws/matches/{match_id}`로 푸시 (구현 검토)

### 3.10 채팅 메시지 발송 — `POST /matches/{match_id}/applications/{application_id}/messages` [T1]
- 인증 필요 (작성자 또는 신청자 본인만 — `application.match.author_id` 또는 `application.applicant_id`)
- 트리거: 신청 발생 직후부터 작성자가 채팅 시작 가능. application.status가 PENDING/ACCEPTED일 때 활성, REJECTED 시 비활성.
- Body(예정): `content` (text)
- Response: 201 Created + 메시지 객체 (`chat_messages.id, content, created_at`)
- WebSocket `/ws/applications/{application_id}`로 실시간 전달

### 3.11 채팅 메시지 조회 — `GET /matches/{match_id}/applications/{application_id}/messages` [T1]
- 인증 필요 (참여자 본인만)
- Query: `before_id` (커서 페이지네이션), `size` (기본 30)
- Response: 메시지 배열 (created_at DESC) + 상대방 마지막 read_at

### 3.12 채팅 스레드 목록 조회 — `GET /matches/{match_id}/chats` [T1]
- 인증 필요 (작성자만 — 자기 매칭의 모든 신청자 스레드 조회)
- Response: 신청자별 스레드 미리보기 배열 (`{ application_id, applicant.nickname, last_message, unread_count, application.status }`)
- 봉사자 시점에서는 자기 application 1건의 스레드만 보이므로 별도 조회 불필요 (`/users/me/chats`로 통합)

### 3.13 봉사 완료 인증 및 후기 작성 — `POST /matches/{match_id}/review` [T1]
- 인증 필요 / Body(예정): `proof_image_urls`, `rating`, `content`

### 3.14 개인별 누적 봉사 이력 통계 — `GET /users/me/volunteer-stats` [T2]
- 인증 필요 (봉사자만)
- Response(예정): `total_count`, `total_hours`, `avg_rating`

---

## 4. 신고/차단 (Report)

> ⚠️ 본 카테고리도 원본 명세에서 API 상세가 누락되어 있어, 아래는 **제안 명세 (TBD)**.

### 4.1 게시글/후기 신고 등록 — `POST /reports` [T1]
- 인증 필요
- Body(예정): `target_type` (`POST` / `REVIEW`), `target_id`, `reason`, `description`
- Errors: 409 (동일 콘텐츠 중복 신고)

### 4.2 채팅 내 유저 신고 등록 — `POST /reports/chat` [T1]
- 인증 필요
- Body(예정): `chat_id`, `target_user_id`, `message_id`, `reason`

### 4.3 특정 사용자 차단 등록 — `POST /users/me/blocks` [T2]
- 인증 필요 / Body(예정): `target_user_id`

### 4.4 차단 사용자 목록 조회 — `GET /users/me/blocks` [T2]
- 인증 필요

### 4.5 차단 해제 — `DELETE /users/me/blocks/{block_id}` [T2]
- 인증 필요 / Response: 204

---

## 5. 지도 / 장소 서비스 (Map)

### 5.1 반려동물 출입 가능 매장 지도 조회 — `GET /maps/stores` [T0]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| lat | float | Y | - | 위도 |
| lng | float | Y | - | 경도 |
| radius | integer | N | 2000 | 검색 반경 (m) |

**Response — 200 OK**
```json
{
  "stores": [
    {
      "store_id": 101,
      "name": "배곧 댕댕카페",
      "latitude": 37.3752,
      "longitude": 126.7281,
      "category": "CAFE",
      "is_pet_allowed": true
    }
  ]
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 좌표 누락 또는 잘못된 형식 |

---

### 5.2 주변 봉사 위치 표시 — `GET /maps/volunteers` [T0]

**인증 필요 (봉사자 권한)**

**Response — 200 OK**
```json
{
  "volunteer_requests": [
    {
      "request_id": 201,
      "title": "정왕동 실외견 병원 이동 부탁드립니다",
      "latitude": 37.3451,
      "longitude": 126.7322,
      "status": "WAITING"
    }
  ]
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 봉사자 권한 없음 |

---

### 5.3 매장 상세 정보 조회 — `GET /maps/stores/{storeId}` [T0]

**인증 불필요** / **Path**: `storeId` (integer)

**Response — 200 OK**
```json
{
  "store_id": 101,
  "name": "배곧 댕댕카페",
  "address": "경기도 시흥시 서울대학로...",
  "phone": "031-123-4567",
  "operating_hours": "10:00 - 22:00",
  "photo_urls": ["url1.jpg", "url2.jpg"],
  "is_pet_allowed": true,
  "rating_avg": 4.5,
  "review_pet_allowed_rate": 0.92
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 404 | 존재하지 않는 매장 |

---

### 5.4 매장 검색 — `GET /maps/stores/search` [T1]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| keyword | string | Y | 상호명 또는 주소 키워드 |

**Response — 200 OK**
```json
{
  "results": [
    {
      "store_id": 101,
      "name": "배곧 댕댕카페",
      "address": "경기도 시흥시 서울대학로...",
      "category": "CAFE"
    }
  ]
}
```

---

### 5.5 지도 마커 필터링 — `GET /maps/stores/filter` [T1]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| category | string | N | `CAFE` / `RESTAURANT` / `PARK` |
| is_pet_allowed | boolean | N | 반려동물 출입 가능 여부 (공식 정보 기준) |

**Response — 200 OK**
```json
{
  "stores": [
    {
      "store_id": 101,
      "name": "배곧 댕댕카페",
      "latitude": 37.3752,
      "longitude": 126.7281,
      "category": "CAFE",
      "is_pet_allowed": true
    }
  ]
}
```

---

### 5.6 신규 매장 정보 등록 — `POST /maps/stores` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 매장 이름 |
| address | string | Y | 매장 주소 |
| category | string | Y | 카테고리 |
| is_pet_allowed | boolean | Y | 반려동물 출입 가능 여부 |

**Response — 201 Created**
```json
{
  "store_id": 105,
  "status": "PENDING"
}
```

> 등록 직후 상태는 `PENDING`. 관리자 검수 후 `APPROVED`로 전환되어야 지도에 노출.

---

### 5.7 매장 정보 수정 — `PUT /maps/stores/{storeId}` [T2]

**인증 필요** (본인 등록 매장 또는 관리자) / **Path**: `storeId`

**Request Body**: 수정할 필드 (5.6과 동일 스키마)

**Response — 200 OK**
```json
{ "message": "성공적으로 처리되었습니다." }
```

---

### 5.8 매장 삭제 — `DELETE /maps/stores/{storeId}` [T2]

**인증 필요** (본인 등록 매장 또는 관리자) / **Path**: `storeId`

**Response — 200 OK**
```json
{ "message": "성공적으로 처리되었습니다." }
```

---

### 5.9 매장 리뷰 조회 — `GET /maps/stores/{storeId}/reviews` [T1]

**인증 불필요** / **Path**: `storeId`

**Response — 200 OK**
```json
{
  "reviews": [
    {
      "review_id": 50,
      "nickname": "댕댕이주인",
      "rating": 5,
      "is_pet_allowed": true,
      "content": "칸막이가 잘 되어 있어서 안심하고 밥 먹었어요!",
      "created_at": "2026-04-16T12:00:00Z"
    }
  ]
}
```

---

### 5.10 매장 리뷰 작성 — `POST /maps/stores/{storeId}/reviews` [T2]

**인증 필요** / **Path**: `storeId`

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| rating | integer | Y | 평점 (1~5) |
| is_pet_allowed | boolean | Y | 방문 당시 반려동물 출입 가능 여부 (체크박스) |
| content | string | Y | 리뷰 내용 |

**Response — 201 Created** (예시)
```json
{
  "review_id": 51,
  "rating": 5,
  "is_pet_allowed": true,
  "content": "...",
  "created_at": "2026-04-16T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 409 | 동일 사용자가 동일 매장에 이미 리뷰 작성함 |

---

### 5.11 매장 리뷰 삭제 — `DELETE /maps/stores/{storeId}/reviews/{reviewId}` [T2]

**인증 필요** (본인 작성만) / **Path**: `storeId`, `reviewId`

**Response — 204 No Content**

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

---

## 부록 A. 도메인 enum 정의

| Enum | 값 |
| --- | --- |
| User.role | `USER`, `VOLUNTEER`, `ADMIN` |
| Pet.species | `DOG`, `CAT`, `OTHER` |
| Notification.category | `VOLUNTEER`, `MATCH`, `REVIEW`, `NEWS`, `POLICY`, `SYSTEM` |
| Match.status | `WAITING`, `MATCHING`, `PROGRESS`, `DONE` |
| VolunteerRequest.status | `PENDING`, `APPROVED`, `REJECTED` |
| Store.category | `CAFE`, `RESTAURANT`, `PARK` |
| Store.status | `PENDING`, `APPROVED`, `REJECTED` |
| Application.status | `PENDING`, `ACCEPTED`, `REJECTED` |

## 부록 B. 미확정 항목 (TBD)

다음 항목은 원본 명세 파일에 API 상세가 누락되어 있어 본 문서에서는 제안 명세를 기재했다. 담당자 확정이 필요하다.

- 3장 매칭(Match) 카테고리의 11개 엔드포인트
- 4장 신고/차단(Report) 카테고리의 4개 엔드포인트
- 5.4~5.11 일부 매장/리뷰 엔드포인트의 에러 코드 표
- 5.6 신규 매장 등록의 성공 상태 코드
