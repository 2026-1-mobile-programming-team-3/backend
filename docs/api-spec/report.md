# API 명세서 — 신고/차단 (Report)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

> ⚠️ 본 카테고리는 부분 구현 상태이다.
> - **구현 완료**: 4.1 (사용자 단위 신고로 확정), 4.3, 4.4, 4.5
> - **미구현(TBD)**: 4.2 (채팅 내 유저 신고)

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
| 400 | 유효성 검증 실패 (사유 길이 등) |
| 401 | 인증 실패 |

---

### 4.2 채팅 내 유저 신고 등록 — `POST /reports/chat` [T1] (TBD)

> ⚠️ 코드 미구현. 아래는 제안 명세.

- 인증 필요
- Body(예정): `chat_id`, `target_user_id`, `message_id`, `reason`

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

---

### 4.4 차단 사용자 목록 조회 — `GET /users/me/blocks` [T2]

**인증 필요**

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
  "total": 1
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
