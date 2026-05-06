# API 명세서 — 사용자 관리 (Auth)

기능 요구사항은 `기능명세서.md`, 프로젝트 전반 정보는 `프로젝트정보.md` 참고.

---

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

### 0.7 공통 입력/보안 정책

본 카테고리 전반에서 적용되는 검증·보안 규칙. 개별 엔드포인트마다 반복 기재하지 않는다.

#### 비밀번호 정책 (signup·비밀번호 변경 공통)
- 길이: **8자 이상 128자 이하** (bcrypt 비용 폭주 방지를 위한 상한)
- 영문자(a–z/A–Z) **1자 이상** 포함
- 숫자 **1자 이상** 포함
- 특수문자 **1자 이상** 포함 (`!@#$%^&*()-_=+[]{};:'",.<>?/\|`~` 중)
- 어긋나면 `400` + 사유 메시지

#### 닉네임 정책
- 양끝 공백 trim 후 **2~20자**, 그 외 `400`

#### 연락처(phone) 정책 — 선택 입력
- `^\+?[0-9\-\s]{9,20}$` 정규식 매칭 필요. 빈 문자열은 `null` 취급.

#### refresh token 회전 정책
- `/auth/refresh` 호출 시 기존 refresh는 **즉시 revoke되고 신규 refresh가 발급**된다. 클라이언트는 응답으로 받은 새 `refresh_token`으로 교체 저장해야 한다 (탈취된 토큰을 7일간 유효 상태로 두지 않기 위함).
- 비밀번호 변경(`PUT /users/me/password`) 또는 계정 탈퇴(`DELETE /users/me`) 시 해당 사용자의 **모든 활성 refresh가 일괄 revoke**된다 — 다른 디바이스는 강제 로그아웃.

#### 로그인 실패 응답
- 이메일 미존재와 비밀번호 불일치는 **동일한 응답·동일한 처리 시간**으로 통일 (타이밍 기반 이메일 열거 차단).

#### 인증 엔드포인트 레이트 리밋 (per-IP, Redis 기반)
- `POST /auth/login`: **10회 / 분**
- `POST /auth/signup`: **10회 / 시간**
- `POST /auth/refresh`: **30회 / 분**
- 초과 시 `429 Too Many Requests`.

#### 어드민 패널 로그인 보호
- SQLAdmin (`/admin`) 로그인 실패가 **5회/IP** 누적되면 **15분 잠금**. 자격 비교는 `hmac.compare_digest`로 타이밍 일정.

---

### 0.8 관리자 권한 (Admin) — 처음 보는 사람 위한 설명

이 섹션은 "관리자만 호출할 수 있는 API"가 어떻게 작동하는지 처음부터 설명한다.

#### 사용자 등급 — `role` 컬럼

모든 사용자는 `users` 테이블에 한 행씩 존재하고, 그 행의 `role` 컬럼에 다음 셋 중 하나가 들어 있다.

| 값 | 의미 | 어떻게 부여되나 |
| --- | --- | --- |
| `USER` | 일반 사용자 | **회원가입하면 자동으로 이 값으로 시작.** 별도 작업 필요 없음 |
| `VOLUNTEER` | 봉사자 | `POST /users/me/volunteer-request`로 신청 → 관리자가 `PATCH /admin/volunteer-requests/{id}`에서 `APPROVE` 하면 자동 승급 |
| `ADMIN` | 운영자 | **회원가입으로는 절대 만들어지지 않는다.** 운영자가 SQLAdmin 화면에서 수동으로 부여 (아래 부트스트랩 절 참고) |

#### "이 요청자가 관리자인가?"는 어떻게 판단하나

- JWT(액세스 토큰) 자체에는 **`role`이 들어 있지 않다.** `sub`(user_id)만 있다.
- 매 요청마다 서버가 토큰을 디코드해서 user_id를 꺼내고, **그때마다 DB에서 `users` 테이블을 한 번 조회한다.** 그 행의 `role` 값이 권위 있는 정보.
- 따라서 어떤 사용자의 `role`이 바뀌면 **다음 요청부터 즉시 반영된다** — 토큰 재발급 안 해도 된다.
- 관리자 전용 API는 모두 URL 경로에 `/admin/`이 들어 있다 (예: `/api/v1/admin/volunteer-requests`). 일반 사용자가 호출하면 `403 관리자 권한이 필요합니다.`

#### 최초의 관리자는 어떻게 만드나 (부트스트랩)

1. 일단 평범하게 회원가입해서 USER로 가입한다 (아무 이메일/비밀번호로).
2. 운영자가 SQLAdmin 화면(`http://{host}/admin`)에 접속해 로그인한다. SQLAdmin 로그인 자격은 일반 사용자 계정과는 별개로 환경변수에 설정된 운영용 자격이다.
3. 좌측 메뉴에서 `Users` 테이블을 열고, 1번에서 가입한 사용자 행을 찾는다.
4. 해당 행의 `role` 컬럼을 `USER` → `ADMIN`으로 수정·저장.
5. 그 사용자 계정으로 다시 로그인해서 받은 access token을 `Authorization: Bearer ...` 헤더에 실어 `/api/v1/admin/...` 엔드포인트를 호출하면 통과.

> 즉, **관리자 만드는 API는 일부러 만들지 않았다.** 권한 부여를 API로 노출하면 무한 권한 상승 위험이 있어서, 운영자만 접근 가능한 SQLAdmin UI에서만 가능하게 막아 둔 것이다.

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
| region_si | string | N | 거주 시 (예: `"시흥시"`). 미설정 시 `null` |
| region_dong | string | N | 거주 동 (예: `"정왕동"`). 미설정 시 `null` |

```json
{
  "email": "user@example.com",
  "password": "securePassword123!",
  "nickname": "댕댕이주인",
  "phone": "010-1234-5678",
  "region_si": "시흥시",
  "region_dong": "정왕동"
}
```

**Response — 201 Created**
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
  "created_at": "2026-04-15T12:00:00Z",
  "updated_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 (비밀번호 조건 미충족, 닉네임 길이, 연락처 정규식 등 — 정책은 §0.7) |
| 409 | 이미 등록된 이메일 |
| 429 | 레이트 리밋 초과 (10회/시간/IP) |

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
| 401 | 이메일 또는 비밀번호 불일치 (이메일 존재 여부와 무관하게 동일 응답·동일 처리 시간 — §0.7 타이밍 정책) |
| 429 | 레이트 리밋 초과 (10회/분/IP) |

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
  "refresh_token": "(새로 발급된 refresh token)",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

> **회전 정책**: 응답의 `refresh_token`은 신규 발급된 값. 요청 본문에 보낸 기존 refresh는 즉시 revoke된다. 클라이언트는 반드시 새 토큰으로 교체 저장. (자세한 정책은 0.7 참고.)

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | refresh token 만료 또는 무효 (이미 회전·revoke된 토큰 포함) |
| 429 | 레이트 리밋 초과 (30회/분/IP) |

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
  "region_si": "시흥시",
  "region_dong": "정왕동",
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
| region_si | string | N | 거주 시. `null` 전송 시 미설정으로 초기화 |
| region_dong | string | N | 거주 동. `null` 전송 시 미설정으로 초기화 |

> region을 클라이언트가 GPS 역지오코딩으로 받은 결과로 갱신할 때도 본 엔드포인트 사용. 시·동 한쪽만 보내면 다른 쪽은 변경 없음 (PATCH 시맨틱).

**Response — 200 OK**
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "새닉네임",
  "phone": "010-9999-8888",
  "profile_image_url": "https://storage.example.com/profiles/1.jpg",
  "role": "USER",
  "region_si": "시흥시",
  "region_dong": "정왕동",
  "created_at": "2026-04-15T12:00:00Z",
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
| new_password | string | Y | 새 비밀번호 — 정책은 §0.7 |

> **부수 효과**: 변경 성공 시 해당 사용자의 **모든 활성 refresh token이 일괄 revoke**된다. 다른 디바이스/세션은 즉시 다음 호출에서 401 → 재로그인 필요.

**Response — 200 OK**
```json
{ "message": "비밀번호가 변경되었습니다." }
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 새 비밀번호 유효성 실패 (§0.7 정책 미충족) |
| 401 | 현재 비밀번호 불일치 |

---

### 1.8 계정 탈퇴 — `DELETE /users/me` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| password | string | Y | 비밀번호 재확인 |
| reason | string | N | 탈퇴 사유 (최대 500자) |

> **부수 효과**: soft delete(`deleted_at` 설정)와 함께 **모든 활성 refresh token이 일괄 revoke**된다.

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
| message | string | Y | 자기소개·지원 동기·봉사 경험 등 (1~2000자) |

```json
{
  "message": "유기동물 봉사활동 2년 경험이 있습니다. 시흥시 인근에 거주하며 차량을 소유하고 있어 이동 지원이 가능합니다."
}
```

**Response — 201 Created**
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
| 409 | 이미 봉사자/관리자이거나 대기 중 요청이 존재 |

---

### 1.13 (관리자) 봉사자 요청 목록 조회 — `GET /admin/volunteer-requests` [T1]

**인증 필요 (관리자 권한)**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| status | string | N | PENDING | `PENDING` / `APPROVED` / `REJECTED` 중 하나 |
| page | integer | N | 1 | 페이지 (1부터) |
| size | integer | N | 20 | 페이지 크기 (1~100) |

**Response — 200 OK**
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
| admin_comment | string | N | (수신만 받고 현재는 저장하지 않음. 향후 컬럼 추가 시 보존 예정) |

**동작**
- `APPROVE`: 요청의 `status` → `APPROVED`, `processed_at` 갱신. 신청자의 `users.role`이 `USER`이면 `VOLUNTEER`로 자동 승급.
- `REJECT`: 요청의 `status` → `REJECTED`, `processed_at` 갱신. `users.role`은 변경되지 않음.
- 이미 처리된 요청(`PENDING`이 아닌 상태)에 다시 호출하면 `409`.

**Response — 200 OK**
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
| 400 | action 값 오류 (`APPROVE`/`REJECT` 외) |
| 401 | 인증 실패 |
| 403 | 관리자 권한 없음 |
| 404 | request_id 없음 |
| 409 | 이미 처리된 요청 |

---

## 부록 A. 도메인 enum 정의

| Enum | 값 |
| --- | --- |
| User.role | `USER`, `VOLUNTEER`, `ADMIN` |
| Pet.species | `DOG`, `CAT`, `OTHER` |
| Notification.category | `VOLUNTEER`, `MATCH`, `REVIEW`, `NEWS`, `POLICY`, `SYSTEM` |
| Match.status | `WAITING`, `MATCHING`, `PROGRESS`, `DONE` |
| VolunteerRequest.status | `PENDING`, `APPROVED`, `REJECTED` |
| Store.category | `CAFE`, `RESTAURANT`, `PARK`, `VET`, `GROOMING` |
| Store.status | `PENDING`, `APPROVED`, `REJECTED` |
| Application.status | `PENDING`, `ACCEPTED`, `REJECTED` |

## 부록 B. 미확정 항목 (TBD)

다음 항목은 원본 명세 파일에 API 상세가 누락되어 있어 본 문서에서는 제안 명세를 기재했다. 담당자 확정이 필요하다.

- 3장 매칭(Match) 미구현 5건: 3.9, 3.10, 3.11, 3.12, 3.13
  (3.1~3.8, 3.14는 구현 완료. 본 문서에 정식 스키마 기재됨)
- 4장 신고/차단(Report) 미구현 1건: 4.2 (채팅 내 유저 신고)
  (4.1, 4.3~4.5는 구현 완료)
