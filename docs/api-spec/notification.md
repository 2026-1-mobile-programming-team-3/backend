# API 명세서 — 알림 (Notification)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/notifications.py` (prefix `/notifications`, tag `Notifications`).

> 카테고리별 push on/off 설정은 `users.md` §4 (`GET/PUT /users/me/notification-settings`) 참고.

---

## 0. 공통

- 안 읽음 카운트는 `read_at IS NULL` 조건의 부분 인덱스(`idx_notifications_user_unread`)로 산출.
- 카테고리 enum: `VOLUNTEER` / `MATCH` / `REVIEW` / `NEWS` / `POLICY` / `SYSTEM`.
- FCM 발송은 `app/services/notification.py:enqueue` 내부에서 DB 적재 + `after_commit` 훅으로 자동 처리. 본 라우터는 인앱 알림 조회/관리 + 디바이스 토큰 등록만 담당.

---

## 1. 알림 목록 조회 — `GET /notifications` [T0]

**인증 필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| is_read | boolean | N | - | `true`: 읽은 알림만, `false`: 안 읽은 알림만 |
| category | string | N | - | `VOLUNTEER` / `MATCH` / `REVIEW` / `NEWS` / `POLICY` / `SYSTEM` |
| page | integer | N | 1 | |
| size | integer | N | 20 | 1~100 |

**Response — 200 OK** (`NotificationListResponse`)
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

**Errors**: 400(잘못된 query param) / 401.

---

## 2. 읽지 않은 알림 개수 조회 — `GET /notifications/unread-count` [T0]

**인증 필요**

**Response — 200 OK** (`UnreadCountResponse`)
```json
{ "unread_count": 3 }
```

**Errors**: 401.

---

## 3. 알림 전체 읽음 처리 — `PATCH /notifications/read-all` [T1]

**인증 필요**

**Response — 200 OK** (`MarkAllReadResponse`)
```json
{
  "updated_count": 5,
  "message": "5건의 알림을 읽음 처리했습니다."
}
```

**Errors**: 401.

---

## 4. 알림 단건 읽음 처리 — `PATCH /notifications/{notification_id}/read` [T0]

**인증 필요** / **Path**: `notification_id` (integer ≥ 1)

알림 카드 클릭 시 호출해 `read_at` 을 갱신한다. 본인 소유의 알림만 처리되며, 이미 읽은 알림에 재호출해도 200 (멱등).

**Response — 200 OK** (`NotificationReadResponse`)
```json
{
  "id": 101,
  "is_read": true,
  "updated": true
}
```

- `updated`: 이번 호출로 `read_at` 이 갱신됐는지(`true`), 아니면 이미 읽은 상태였는지(`false`).

**Errors**: 401 / 404(본인 소유의 해당 알림이 존재하지 않음).

---

## 5. 푸시 알림 디바이스 토큰 등록 — `POST /notifications/devices` [T0]

**인증 필요**

**Request Body** (`DeviceRegisterRequest`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| fcm_token | string | Y | FCM 디바이스 토큰 (1자 이상) |
| device_name | string | N | 기기명 (디버깅용, 최대 100자) |

**Response — 201 Created** (`DeviceRegisteredResponse`)
```json
{
  "id": 1,
  "registered_at": "2026-04-15T12:00:00Z"
}
```

> 동일 `fcm_token` 재등록 시 기존 row 의 `updated_at` 갱신 — 별도 409 없음 (멱등). 무효 토큰(`UNREGISTERED`/`NOT_FOUND`)은 FCM 발송 시 자동 정리.

**Errors**: 401 / 422(`fcm_token` 누락 등).
