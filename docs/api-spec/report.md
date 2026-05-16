# API 명세서 — 신고 (Report)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/reports.py` (prefix `/reports`, tag `Reports`).

> 사용자 차단(`/users/me/blocks/*`)은 `blocks.md` 참고.

---

## 0. 공통 — 신고 정책

- **본인 신고 금지**: `target_user_id == reporter_id` 면 400.
- **중복 신고 차단(USER 한정)**: `(reporter_id, target_user_id)` 부분 유니크 (`WHERE report_type = 'USER'`) — `report_type='USER'` 인 두 번째 신고는 409. 채팅 메시지 단위 신고(`POST /reports/chat`)는 메시지마다 자유롭게 작성 가능.
- **이유 길이**: `reason` 1~2,000자.
- **레이트 리밋**: `POST /reports`, `POST /reports/chat` 각각 **20회 / 시간 / IP**. 초과 시 429.

DB 모델 (`app/models/report.py:Report`):
- `report_type` enum: `USER` / `CHAT` (default `USER`).
- `chat_room_id` / `message_id`: `CHAT` 신고 시 필수, FK `ON DELETE SET NULL`.
- CHECK: `report_type = 'USER' OR (chat_room_id IS NOT NULL AND message_id IS NOT NULL)`.

---

## 1. 사용자 신고 — `POST /reports` [T1]

**인증 필요**

**Request Body** (`ReportCreateRequest`)

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

**Response — 201 Created** (`ReportCreatedResponse`)
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
| 400 | 유효성 검증 실패 (사유 길이 1~2000자, 본인 신고 등) |
| 401 | 인증 실패 |
| 404 | 대상 사용자 없음 |
| 409 | 동일 사용자에 대해 이미 신고함 (`report_type='USER'` 중복) |
| 429 | 레이트 리밋 초과 (20회/시간/IP) |

---

## 2. 채팅 내 유저 신고 — `POST /reports/chat` [T1]

**인증 필요** (채팅방 참여자만)

**Request Body** (`ChatReportCreateRequest`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| chat_id | integer | Y | `chat_rooms.id` |
| target_user_id | integer | Y | 신고 대상 (해당 방의 상대방) |
| message_id | integer | Y | 신고할 메시지 (해당 방 소속, `sender_id == target_user_id`) |
| reason | string | Y | 신고 사유 (1~2000자) |

```json
{
  "chat_id": 10,
  "target_user_id": 5,
  "message_id": 100,
  "reason": "욕설"
}
```

**Response — 201 Created** (`ChatReportCreatedResponse`)
```json
{
  "report_id": 2,
  "status": "RECEIVED",
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 본인 신고, `target_user_id` 가 방 상대방이 아님, 메시지 `sender_id` 가 `target_user_id` 가 아님 |
| 401 | 인증 실패 |
| 403 | 채팅 참여자 아님 |
| 404 | 채팅방 또는 메시지 없음 |
| 429 | 레이트 리밋 초과 (20회/시간/IP) |
