# API 명세서 — 신고/차단 (Report)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

> 구현 상태: 4.1~4.5 모두 정식 명세.

---

## 4.0 공통 — 신고·차단 정책

### 신고 (Report)
- **본인 신고 금지**: `target_user_id == reporter` 면 400.
- **중복 신고 차단(USER 한정)**: `(reporter_id, target_user_id)` 부분 유니크 — `report_type='USER'` 인 두 번째 신고는 409. 채팅 메시지 단위 신고(`POST /reports/chat`)는 메시지마다 자유롭게 작성 가능.
- **이유 길이**: `reason` 1~2,000자.
- **레이트 리밋**: `POST /reports`, `POST /reports/chat` 각각 **20회 / 시간 / IP**. 초과 시 429.

### 차단 (Block)
- **본인 차단 금지**: 400.
- **중복 차단 차단**: `(blocker_id, blocked_id)` 유니크 — 두 번째 시도는 409.
- **레이트 리밋**: `POST /users/me/blocks`는 **30회 / 시간 / IP**. 초과 시 429.
- **차단의 가시성 효과** (= 차단된 사용자가 내 화면에서 어떻게 사라지는가):
  - `GET /matches`: 양방향 차단 작성자의 글 제외
  - `GET /matches/{id}/applications`: 작성자가 차단한 신청자의 신청 제외
  - `GET /maps/volunteers`: 양방향 차단 작성자의 봉사 위치 제외
  - 단일 리소스 직접 조회(`GET /matches/{id}` 등)는 ID를 알고 호출하는 경우라 별도 차단 필터를 적용하지 않는다.
- 차단 해제(`DELETE /users/me/blocks/{block_id}`) 시 가시성은 즉시 복원.

---

## 4. 신고/차단 (Report)

### 4.1 사용자 신고 등록 — `POST /reports` [T1]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| target_user_id | integer | Y | 신고 대상 사용자 id |
| reason | string | Y | 신고 사유 (1~2000자) |

```json
{
  "target_user_id": 12,
  "reason": "허위 정보로 봉사 신청을 반복합니다."
}
```

**Response — 201 Created**
```json
{
  "id": 1,
  "target_user_id": 12,
  "reason": "허위 정보로 봉사 신청을 반복합니다.",
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검증 실패 (사유 길이 1~2,000자, 본인 신고 등) |
| 401 | 인증 실패 |
| 404 | 대상 사용자 없음 |
| 409 | 동일 사용자에 대해 이미 신고함 |
| 429 | 레이트 리밋 초과 (20회/시간/IP) |

---

### 4.2 채팅 내 유저 신고 등록 — `POST /reports/chat` [T1]

**인증 필요** (채팅방 참여자만)

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| chat_id | integer | Y | `chat_rooms.id` |
| target_user_id | integer | Y | 신고 대상 (해당 방의 상대방) |
| message_id | integer | Y | 신고할 메시지 (해당 방 소속, sender == target_user_id) |
| reason | string | Y | 신고 사유 (1~2000자) |

```json
{ "chat_id": 10, "target_user_id": 5, "message_id": 100, "reason": "욕설" }
```

**Response — 201 Created**
```json
{ "report_id": 2, "status": "RECEIVED", "created_at": "2026-04-15T12:00:00Z" }
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 본인 신고, target_user_id가 방 상대방이 아님, 메시지 sender가 target이 아님 |
| 401 | 인증 실패 |
| 403 | 채팅 참여자 아님 |
| 404 | 채팅방 또는 메시지 없음 |
| 429 | 레이트 리밋 초과 |

---

### 4.3 특정 사용자 차단 등록 — `POST /users/me/blocks` [T2]

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| target_user_id | integer | Y | 차단 대상 사용자 id |

```json
{ "target_user_id": 12 }
```

**Response — 201 Created**
```json
{
  "block_id": 1,
  "target_user_id": 12,
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 본인을 차단 시도 |
| 401 | 인증 실패 |
| 404 | 대상 사용자 없음 (또는 탈퇴함) |
| 409 | 이미 차단한 사용자 |
| 429 | 레이트 리밋 초과 (30회/시간/IP) |

> **차단 즉시 효과**: 등록 직후 §4.0의 가시성 필터가 적용된다 — 다음 요청부터 해당 사용자의 글·신청·봉사 위치가 숨겨진다.

---

### 4.4 차단 사용자 목록 조회 — `GET /users/me/blocks` [T2]

**인증 필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | integer | N | 1 | |
| size | integer | N | 20 | (1~100) |

**Response — 200 OK**
```json
{
  "items": [
    {
      "block_id": 1,
      "target_user_id": 12,
      "target_nickname": "트롤유저",
      "created_at": "2026-04-15T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

> `target_nickname`은 대상 사용자가 탈퇴한 경우 `null`.

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |

---

### 4.5 차단 해제 — `DELETE /users/me/blocks/{block_id}` [T2]

**인증 필요** (본인 차단 항목만) / **Path**: `block_id`

**Response — 204 No Content** (응답 본문 없음)

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 404 | `block_id` 없음 또는 본인이 만든 차단이 아님 |
