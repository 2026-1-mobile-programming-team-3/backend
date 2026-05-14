# API 명세서 — 알림 (Notification)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

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

### 2.5 알림 단건 읽음 처리 — `PATCH /notifications/{notification_id}/read` [T0]

**인증 필요** / **Path**: `notification_id` (integer ≥ 1)

알림 카드 클릭 시 호출해 `read_at` 을 갱신한다. 본인 소유의 알림만 처리되며, 이미 읽은 알림에 재호출해도 200 (멱등).

**Response — 200 OK**
```json
{
  "id": 101,
  "is_read": true,
  "updated": true
}
```

- `updated`: 이번 호출로 `read_at` 이 갱신됐는지(`true`), 아니면 이미 읽은 상태였는지(`false`).

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 404 | 본인 소유의 해당 알림이 존재하지 않음 |

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
