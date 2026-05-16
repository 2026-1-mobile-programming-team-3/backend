# API 명세서 — 사용자 차단 (`/users/me/blocks`)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/blocks.py` (prefix `/users/me/blocks`, tag `blocks`).

> 신고(`/reports/*`)는 `report.md` 참고.

---

## 0. 공통 — 차단 정책

- **본인 차단 금지**: 400.
- **중복 차단 차단**: `UNIQUE(blocker_id, blocked_id)` — 두 번째 시도는 409.
- **레이트 리밋**: `POST /users/me/blocks` 는 **30회 / 시간 / IP**. 초과 시 429.
- **차단의 가시성 효과** (차단된 사용자가 내 화면에서 어떻게 사라지는가):
  - `GET /matches`: 양방향 차단 작성자의 글 제외
  - `GET /matches/{id}/applications`: 작성자가 차단한 신청자의 신청 제외
  - `GET /matches/{id}/chats`: 양방향 차단된 신청자의 스레드 제외
  - `GET /maps/volunteers`: 양방향 차단 작성자의 봉사 위치 제외
  - 채팅 메시지 전송 (`POST /matches/{m}/applications/{a}/messages`): 양방향 차단 시 403
  - WebSocket `/ws/applications/{a}`: 양방향 차단 시 close `4403`
- 단일 리소스 직접 조회(`GET /matches/{id}` 등)는 ID를 알고 호출하는 경우라 별도 차단 필터를 적용하지 않는다.
- 차단 해제 시 가시성은 즉시 복원.

---

## 1. 사용자 차단 등록 — `POST /users/me/blocks` [T2]

**인증 필요**

**Request Body** (`BlockCreateRequest`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| target_user_id | integer | Y | 차단 대상 사용자 id (> 0) |

```json
{ "target_user_id": 12 }
```

**Response — 201 Created** (`BlockCreatedResponse`)
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
| 400 | 본인을 차단 시도 (CHECK `blocker_id <> blocked_id` 위반) |
| 401 | 인증 실패 |
| 404 | 대상 사용자 없음 (또는 탈퇴함) |
| 409 | 이미 차단한 사용자 |
| 429 | 레이트 리밋 초과 (30회/시간/IP) |

> **차단 즉시 효과**: 등록 직후 §0 의 가시성 필터가 적용된다 — 다음 요청부터 해당 사용자의 글·신청·봉사 위치·채팅 스레드가 숨겨진다.

---

## 2. 차단 사용자 목록 조회 — `GET /users/me/blocks` [T2]

**인증 필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | integer | N | 1 | |
| size | integer | N | 20 | 1~100 |

**Response — 200 OK** (`BlockListResponse`)
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

> `target_nickname` 은 대상 사용자가 탈퇴한 경우 `null`.

**Errors**: 401.

---

## 3. 차단 해제 — `DELETE /users/me/blocks/{block_id}` [T2]

**인증 필요** (본인 차단 항목만) / **Path**: `block_id`

**Response — 204 No Content** (응답 본문 없음)

**Errors**: 401 / 404(`block_id` 없음 또는 본인이 만든 차단이 아님).
