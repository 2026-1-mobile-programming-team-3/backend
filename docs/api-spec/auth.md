# API 명세서 — 인증 / 공통 (Auth)

본 문서는 **공통 사항(Base URL·헤더·에러 코드·보안 정책·도메인 enum)** 과 **인증 라우터(`/auth/*`) 4개 엔드포인트** 를 다룬다. 라우터 코드: `app/api/v1/auth.py` (prefix `/auth`, tag `auth`).

도메인별 명세 위치:

| 라우터 | prefix | 문서 |
| --- | --- | --- |
| `auth` | `/auth` | 본 문서 |
| `users` | `/users/me` | `users.md` |
| `pets` | `/users/me/pets` | `pets.md` |
| `favorites` | `/users/me/favorites` | `favorites.md` |
| `blocks` | `/users/me/blocks` | `blocks.md` |
| `news` | `/news` | `news.md` |
| `maps` | `/maps` | `map.md` |
| `matches` | `/matches` (채팅 REST 포함) | `match.md` |
| `chats` (WS) | `/ws` | `chat.md` |
| `notifications` | `/notifications` | `notification.md` |
| `reports` | `/reports` | `report.md` |
| `home` | `/home` | `home.md` |
| `geo` | `/geo` | `geo.md` |
| `admin` | `/admin` | `admin.md` |

---

## 0. 공통 사항

### 0.1 Base URL
```
https://{host}/api/v1
```
- OpenAPI: `GET /docs`, ReDoc: `GET /redoc`
- WebSocket: `wss://{host}/api/v1/ws/...` (자세한 채널은 `chat.md`)

### 0.2 공통 헤더

| 헤더 | 값 | 필수 | 비고 |
| --- | --- | --- | --- |
| Content-Type | application/json | 요청 본문이 있는 경우 Y | |
| Authorization | `Bearer {access_token}` | 인증 필요 API에서 Y | JWT |

### 0.3 인증

- JWT 기반.
- 로그인 시 `access_token`(30분), `refresh_token`(7일) 발급.
- Access Token 만료 시 `POST /auth/refresh` 로 갱신.
- JWT 페이로드에는 `sub`(user_id) 만 들어가며 **`role` 은 들어가지 않는다**. 매 요청마다 DB `users.role` 을 재조회 — 역할 변경은 토큰 재발급 없이 다음 요청부터 즉시 반영. 관리자 부트스트랩은 `admin.md` §0.

### 0.4 공통 에러 코드

| 상태 코드 | 의미 |
| --- | --- |
| 400 | 요청 본문/파라미터 유효성 검증 실패 |
| 401 | 인증 실패 (토큰 미제공/만료/무효) |
| 403 | 권한 없음 (역할 부족, 본인 소유 아님) |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복 등록, 이미 처리됨 등) |
| 422 | Pydantic 검증 실패 (필드 타입/필수값) |
| 429 | 레이트 리밋 초과 |
| 500 | 서버 내부 오류 |
| 502 | 외부 API 호출 실패 (카카오·네이버 등) |

### 0.5 공통 응답 컨벤션

- 성공 응답은 도메인별 JSON 객체.
- 페이지네이션: `{ "items": [...], "total": N, "page": N, "size": N }`.
- 시각: ISO-8601 UTC (`2026-04-15T12:00:00Z`).
- 날짜: `YYYY-MM-DD`. 시간: `HH:MM` 또는 `HH:MM:SS`.

### 0.6 우선순위/난이도 표기 약어

- 우선순위: T0 (필수) / T1 (부가) / T2 (확장)
- 난이도: 하 / 중 / 상

### 0.7 공통 입력/보안 정책

본 문서 전반에서 적용되는 검증·보안 규칙. 개별 엔드포인트마다 반복 기재하지 않는다.

#### 비밀번호 정책 (signup·비밀번호 변경 공통)
- 길이: **8자 이상 128자 이하** (bcrypt 비용 폭주 방지를 위한 상한)
- 영문자(a–z/A–Z) **1자 이상** 포함
- 숫자 **1자 이상** 포함
- 특수문자 **1자 이상** 포함 (`!@#$%^&*()-_=+[]{};:'",.<>?/\|`~` 중)
- 어긋나면 `400` + 사유 메시지

#### 닉네임 정책
- 양끝 공백 trim 후 **2~20자**, 그 외 `400`. DB `users.nickname` 은 UNIQUE.

#### 연락처(phone) 정책 — 선택 입력
- `^\+?[0-9\-\s]{9,20}$` 정규식 매칭 필요. 빈 문자열은 `null` 취급.

#### refresh token 회전 정책
- `POST /auth/refresh` 호출 시 기존 refresh는 **즉시 revoke되고 신규 refresh가 발급**된다. 클라이언트는 응답으로 받은 새 `refresh_token` 으로 교체 저장해야 한다 (탈취된 토큰을 7일간 유효 상태로 두지 않기 위함).
- 비밀번호 변경(`PUT /users/me/password`) 또는 계정 탈퇴(`DELETE /users/me`) 시 해당 사용자의 **모든 활성 refresh가 일괄 revoke** — 다른 디바이스는 강제 로그아웃.

#### 로그인 실패 응답
- 이메일 미존재와 비밀번호 불일치는 **동일한 응답·동일한 처리 시간** 으로 통일 (타이밍 기반 이메일 열거 차단).

#### 인증 엔드포인트 레이트 리밋 (per-IP, Redis 기반)
- `POST /auth/login`: **10회 / 분**
- `POST /auth/signup`: **10회 / 시간**
- `POST /auth/refresh`: **30회 / 분**
- 초과 시 `429 Too Many Requests`.

#### 어드민 패널 로그인 보호 (`admin.md` §0.4 참고)
- SQLAdmin (`/admin`) 로그인 실패가 **5회/IP** 누적되면 **15분 잠금**.

---

## 1. 인증 라우터 (`/auth`)

### 1.1 회원가입 — `POST /auth/signup` [T0]

**Request Headers**: `Content-Type: application/json` (인증 헤더 불필요)

**Request Body** (`SignupRequest`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 이메일 (로그인 ID) |
| password | string | Y | 비밀번호 — 정책은 §0.7 |
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

**Response — 201 Created** (`UserResponse`)
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
| 400 | 유효성 검증 실패 (비밀번호 조건, 닉네임 길이, 연락처 정규식 등 — §0.7) |
| 409 | 이미 등록된 이메일 또는 닉네임 |
| 429 | 레이트 리밋 초과 (10회/시간/IP) |

---

### 1.2 로그인 — `POST /auth/login` [T0]

**Request Body** (`LoginRequest`)

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

**Response — 200 OK** (`LoginResponse`)
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
| 401 | 이메일 또는 비밀번호 불일치 (이메일 존재 여부와 무관 — §0.7 타이밍 정책) |
| 429 | 레이트 리밋 초과 (10회/분/IP) |

---

### 1.3 토큰 갱신 — `POST /auth/refresh` [T0]

**Request Body** (`TokenRefreshRequest`)

| 필드 | 타입 | 필수 |
| --- | --- | --- |
| refresh_token | string | Y |

```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIs..." }
```

**Response — 200 OK** (`TokenRefreshResponse`)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "(새로 발급된 refresh token)",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

> **회전 정책**: 응답의 `refresh_token` 은 신규 발급된 값. 요청 본문에 보낸 기존 refresh 는 즉시 revoke. 클라이언트는 반드시 새 토큰으로 교체 저장 (§0.7).

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | refresh token 만료 또는 무효 (이미 회전·revoke 된 토큰 포함) |
| 429 | 레이트 리밋 초과 (30회/분/IP) |

---

### 1.4 로그아웃 — `POST /auth/logout` [T0]

**인증 필요** (Authorization 헤더 — access token)

**Request Body** (`LogoutRequest`)
```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIs..." }
```

**Response — 200 OK** (`MessageResponse`)
```json
{ "message": "로그아웃되었습니다." }
```

**Errors**: 401(access token 만료/무효).

---

## 부록 A. 도메인 enum 정의

코드 기준 (`app/models/enums.py`):

| Enum | 값 |
| --- | --- |
| `UserRole` | `USER`, `VOLUNTEER`, `ADMIN` |
| `PetSpecies` | `DOG`, `CAT`, `OTHER` |
| `PetGender` | `MALE`, `FEMALE`, `UNKNOWN` |
| `VolunteerBadgeTier` | `NONE`, `SEED`, `FLOWER`, `FRUIT`, `TREE` |
| `NotificationCategory` | `VOLUNTEER`, `MATCH`, `REVIEW`, `NEWS`, `POLICY`, `SYSTEM` |
| `MatchStatus` | `WAITING`, `MATCHING`, `PROGRESS`, `DONE` |
| `ApplicationStatus` | `PENDING`, `ACCEPTED`, `REJECTED` |
| `VolunteerRequestStatus` | `PENDING`, `APPROVED`, `REJECTED` |
| `StoreCategory` | `CAFE`, `RESTAURANT`, `PARK` |
| `StoreStatus` | `PENDING`, `APPROVED`, `REJECTED` |
| `ReportType` | `USER`, `CHAT` |
