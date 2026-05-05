# API 명세서 — 중성화 이동 지원 매칭 (Match)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

> ⚠️ 본 카테고리는 부분 구현 상태이다.
> - **구현 완료**: 3.1~3.8, 3.14 — 본 문서에 정식 스키마 기재.
> - **미구현(TBD)**: 3.9~3.13 — 원본 명세 누락 + 코드 부재 상태이며 담당자 확정 후 갱신 예정.

---

## 3.0 공통 — 입력 제약·차단 가시성

- **content / message 길이**: 매칭 본문(`content`) **1~10,000자**, 신청 메시지(`message`) **0~2,000자**, 후기 본문은 후속 명세에서 정의. DB 컬럼은 TEXT지만 애플리케이션 레이어에서 캡 적용해 거대 페이로드 차단.
- **좌표(`latitude`/`longitude`)**: NaN/Inf 거부(유한값만 허용). 둘 중 하나만 보내면 422.
- **차단 가시성**: `POST /users/me/blocks`로 차단된 사용자(혹은 본인을 차단한 사용자)와의 양방향 글이 다음 엔드포인트에서 자동으로 숨겨진다.
  - `GET /matches` — 양방향 차단 작성자의 글 제외
  - `GET /matches/{id}/applications` — 작성자가 차단한 신청자의 신청 제외
  - `GET /maps/volunteers` — 양방향 차단 작성자의 봉사 위치 제외
  - 단, 단일 리소스 조회(`GET /matches/{id}`)는 ID를 직접 알고 있는 경우라 별도 차단 필터가 적용되지 않는다.
- **신청 처리 동시성**: `PATCH /matches/{id}/applications/{aid}`는 매칭/신청 row를 `SELECT ... FOR UPDATE`로 락 — 동시 ACCEPT 레이스에서 정확히 1건만 ACCEPTED로 확정.

---

## 3. 중성화 이동 지원 매칭 (Match)

### 3.1 이동 지원 요청 글 작성 — `POST /matches` [T0]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| title | string | Y | 요청 글 제목 (1~100자) |
| content | string | Y | 요청 글 본문 (1~10,000자) |
| latitude | float | Y | 위도 (-90 ~ 90, 유한값) |
| longitude | float | Y | 경도 (-180 ~ 180, 유한값) |
| address | string | N | 주소 (최대 255자) |
| desired_date | string | N | 희망 날짜 (`YYYY-MM-DD`) |
| pet_id | integer | N | 반려동물 id (본인 소유) |

```json
{
  "title": "정왕동 실외견 병원 이동 부탁드립니다",
  "content": "중성화 수술 위해 동물병원까지 이동 봉사를 부탁드립니다.",
  "latitude": 37.3451,
  "longitude": 126.7322,
  "address": "경기도 시흥시 정왕동 ...",
  "desired_date": "2026-05-10",
  "pet_id": 3
}
```

**Response — 201 Created**
```json
{
  "match_id": 1,
  "status": "WAITING",
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 |
| 401 | 인증 실패 |
| 404 | `pet_id`가 본인 소유가 아니거나 존재하지 않음 |

---

### 3.2 이동 지원 요청 글 수정 — `PATCH /matches/{match_id}` [T1]

**인증 필요** (본인 작성 글만) / **Path**: `match_id`

**Request Body** (변경할 필드만 전송 — 모두 옵셔널)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| title | string | N | 글 제목 (1~100자) |
| content | string | N | 글 내용 (1~10,000자) |
| latitude | float | N | 위도. `longitude`와 함께 보내야 함 (유한값) |
| longitude | float | N | 경도. `latitude`와 함께 보내야 함 (유한값) |
| address | string | N | 주소 (최대 255자) |
| desired_date | string | N | 희망 날짜 (`YYYY-MM-DD`) |
| pet_id | integer | N | 반려동물 id (본인 소유) |

> 매칭 status가 `WAITING` 또는 `MATCHING`일 때만 수정 가능. `PROGRESS`/`DONE` 상태에서는 409.

**Response — 200 OK**
```json
{ "message": "성공적으로 처리되었습니다." }
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 / 422 | 유효성 검증 실패 (lat/lng 한쪽만 전송 등) |
| 401 | 인증 실패 |
| 403 | 본인이 작성한 매칭 요청이 아님, 또는 pet_id가 본인 소유 아님 |
| 404 | match_id 또는 pet_id 없음 |
| 409 | 이미 진행 중이거나 완료된 매칭 |

---

### 3.3 이동 지원 요청 글 삭제 — `DELETE /matches/{match_id}` [T1]

**인증 필요** (본인 작성 글만) / **Path**: `match_id`

Soft delete — `deleted_at = NOW()`로 표시. 이후 조회·수정 시 404. 매칭 status가 `WAITING` 또는 `MATCHING`일 때만 가능.

**Response — 204 No Content** (응답 본문 없음)

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 본인이 작성한 매칭 요청이 아님 |
| 404 | match_id 없음 (또는 이미 삭제됨) |
| 409 | 이미 진행 중이거나 완료된 매칭 |

---

### 3.4 이동 지원 요청 목록 조회 — `GET /matches` [T0]

**인증 필요**

> 양방향 차단 사용자(내가 차단했거나 나를 차단한)의 작성 글은 결과에서 제외된다 (§3.0).

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| status | string | N | - | `WAITING` / `MATCHING` / `PROGRESS` / `DONE` |
| region | string | N | - | 지역 필터 (최대 50자) |
| from_date | string | N | - | 희망 날짜 시작 (`YYYY-MM-DD`) |
| to_date | string | N | - | 희망 날짜 종료 (`YYYY-MM-DD`) |
| page | integer | N | 1 | |
| size | integer | N | 20 | (1~100) |

**Response — 200 OK**
```json
{
  "items": [
    {
      "match_id": 1,
      "title": "정왕동 실외견 병원 이동 부탁드립니다",
      "address": "경기도 시흥시 정왕동 ...",
      "latitude": 37.3451,
      "longitude": 126.7322,
      "desired_date": "2026-05-10",
      "status": "WAITING",
      "author_nickname": "댕댕이주인",
      "created_at": "2026-04-15T12:00:00Z"
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
| 400 | 잘못된 query parameter |
| 401 | 인증 실패 |

---

### 3.5 특정 요청 상세 정보 조회 — `GET /matches/{match_id}` [T0]

**인증 필요** / **Path**: `match_id` (integer)

**Response — 200 OK**
```json
{
  "match_id": 1,
  "author": { "user_id": 5, "nickname": "댕댕이주인" },
  "pet": {
    "pet_id": 3,
    "name": "초코",
    "species": "DOG",
    "is_neutered": false
  },
  "title": "정왕동 실외견 병원 이동 부탁드립니다",
  "content": "...",
  "address": "경기도 시흥시 정왕동 ...",
  "latitude": 37.3451,
  "longitude": 126.7322,
  "desired_date": "2026-05-10",
  "status": "WAITING",
  "applications_count": 2,
  "created_at": "2026-04-15T12:00:00Z"
}
```

> `pet`은 작성자가 `pet_id`를 지정하지 않았거나 이후 삭제된 경우 `null`.

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 404 | 존재하지 않는 `match_id` |

---

### 3.6 봉사 신청하기 — `POST /matches/{match_id}/applications` [T0]

**인증 필요** (별도 역할 게이팅 없음 — 모든 로그인 사용자가 신청 가능)

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| message | string | N | 신청 메시지 (최대 2000자) |

**Response — 201 Created**
```json
{
  "application_id": 10,
  "match_id": 1,
  "applicant_id": 7,
  "status": "PENDING",
  "created_at": "2026-04-15T13:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 본인 매칭에 신청, 이미 신청함, 모집 종료된 매칭 등 |
| 401 | 인증 실패 |
| 404 | 존재하지 않는 `match_id` |

---

### 3.7 신청자 목록 조회 (작성자용) — `GET /matches/{match_id}/applications` [T0]

**인증 필요** (요청 작성자만)

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | integer | N | 1 | |
| size | integer | N | 20 | (1~100) |

> 작성자가 차단한 사용자의 신청은 결과에서 제외된다 (§3.0 차단 가시성).

**Response — 200 OK**
```json
{
  "items": [
    {
      "application_id": 10,
      "applicant": { "applicant_id": 7, "nickname": "봉사자A" },
      "message": "이동 지원 가능합니다.",
      "status": "PENDING",
      "created_at": "2026-04-15T13:00:00Z"
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
| 403 | 작성자 아님 |
| 404 | 존재하지 않는 `match_id` |

---

### 3.8 봉사자 매칭 수락/거절 — `PATCH /matches/{match_id}/applications/{application_id}` [T0]

**인증 필요** (요청 작성자만) / **Path**: `match_id`, `application_id`

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| action | string | Y | `ACCEPT` 또는 `REJECT` |

**동작**
- `ACCEPT`: 해당 application의 `status` → `ACCEPTED`. 같은 매칭의 다른 PENDING application은 자동 `REJECTED`. `matches.status = 'PROGRESS'`로 전이.
- `REJECT`: 해당 application의 `status` → `REJECTED`. 다른 신청에는 영향 없음.

> **동시성**: 매칭/신청 row를 `SELECT ... FOR UPDATE`로 락. 두 클라이언트가 같은 매칭의 서로 다른 신청을 동시에 ACCEPT 해도 정확히 1건만 ACCEPTED로 확정되고 나머지는 409.

**Response — 200 OK**
```json
{
  "application_id": 10,
  "status": "ACCEPTED",
  "match_status": "PROGRESS"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | `action` 값 오류, 이미 처리된 application 등 |
| 401 | 인증 실패 |
| 403 | 작성자 아님 |
| 404 | `match_id` 또는 `application_id` 없음 |

---

### 3.9 매칭 상태 실시간 업데이트 — `PATCH /matches/{match_id}/status` [T1] (TBD)

> ⚠️ 코드 미구현. 아래는 제안 명세.

- 인증 필요
- Body(예정): `status` (`PROGRESS` / `DONE`)
- WebSocket 채널 `/ws/matches/{match_id}`로 푸시 (구현 검토)

---

### 3.10 채팅 메시지 발송 — `POST /matches/{match_id}/applications/{application_id}/messages` [T1] (TBD)

> ⚠️ 코드 미구현. 아래는 제안 명세.

- 인증 필요 (작성자 또는 신청자 본인만 — `application.match.author_id` 또는 `application.applicant_id`)
- 트리거: 신청 발생 직후부터 작성자가 채팅 시작 가능. application.status가 PENDING/ACCEPTED일 때 활성, REJECTED 시 비활성.
- Body(예정): `content` (text)
- Response: 201 Created + 메시지 객체 (`chat_messages.id, content, created_at`)
- WebSocket `/ws/applications/{application_id}`로 실시간 전달

---

### 3.11 채팅 메시지 조회 — `GET /matches/{match_id}/applications/{application_id}/messages` [T1] (TBD)

> ⚠️ 코드 미구현. 아래는 제안 명세.

- 인증 필요 (참여자 본인만)
- Query: `before_id` (커서 페이지네이션), `size` (기본 30)
- Response: 메시지 배열 (created_at DESC) + 상대방 마지막 read_at

---

### 3.12 채팅 스레드 목록 조회 — `GET /matches/{match_id}/chats` [T1] (TBD)

> ⚠️ 코드 미구현. 아래는 제안 명세.

- 인증 필요 (작성자만 — 자기 매칭의 모든 신청자 스레드 조회)
- Response: 신청자별 스레드 미리보기 배열 (`{ application_id, applicant.nickname, last_message, unread_count, application.status }`)
- 봉사자 시점에서는 자기 application 1건의 스레드만 보이므로 별도 조회 불필요 (`/users/me/chats`로 통합)

---

### 3.13 봉사 완료 인증 및 후기 작성 — `POST /matches/{match_id}/review` [T1] (TBD)

> ⚠️ 코드 미구현. 아래는 제안 명세.

- 인증 필요 / Body(예정): `proof_image_urls`, `rating`, `content`

---

### 3.14 개인별 누적 봉사 이력 통계 — `GET /users/me/volunteer-stats` [T2]

**인증 필요 (봉사자 권한 — `VOLUNTEER` 또는 `ADMIN`)**

요청자 본인이 봉사자로 매칭에 참여(ACCEPTED)했고 매칭 status가 DONE인 건수, 본인이 reviewee로 받은 후기 평점 평균을 반환한다.

**Response — 200 OK**
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
| total_hours | float | 누적 봉사 시간. ⚠️ 시간 추적 컬럼이 아직 없어 현재 항상 `0.0`. 추후 활동 로그가 추가되면 보강 예정. |
| avg_rating | float \| null | `match_reviews.reviewee_id = me`인 후기들의 평균 평점. 후기가 한 건도 없으면 `null`. |

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 봉사자 권한 없음 (`USER` 토큰으로 호출) |
