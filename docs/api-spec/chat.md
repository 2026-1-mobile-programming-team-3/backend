# API 명세서 — 채팅 (Chat)

채팅 REST 엔드포인트는 매칭 도메인(`match.md` §3.10~3.12)에 포함되어 있다. 본 문서는 WebSocket 채널과 채팅방 모델의 운영 노트.

---

## 모델

- `chat_rooms (id, application_id UNIQUE, created_at)` — 신청 1건당 채팅방 1개 (1:1).
- `chat_messages (id, chat_room_id FK, sender_id FK→users SET NULL, content, read_at, created_at)`.

채팅방은 첫 메시지 시점에 `POST /matches/{m}/applications/{a}/messages` 가 자동 생성한다 — 명시적 생성 API는 없다.

---

## WebSocket — `/api/v1/ws/applications/{application_id}`

실시간 메시지 수신 채널. 송신은 REST `POST .../messages` 가 담당하고, 본 채널은 broadcast 만 받는다.

### 인증
- 핸드쉐이크 시 JWT를 query `?token=<JWT>` 또는 `Sec-WebSocket-Protocol: bearer.<JWT>` 형태로 전달.
- 인증 실패 → close code `4401`.

### 권한
- 참여자(작성자 또는 신청자)만 연결 가능. 외부인은 close code `4403`.
- application.status 가 `REJECTED` 면 close code `4403` (PENDING/ACCEPTED 만 활성).
- 양방향 차단된 상대인 경우 close code `4403`.

### 페이로드 (서버 → 클라이언트)
```json
{
  "type": "message.created",
  "id": 100,
  "room_id": 7,
  "application_id": 20,
  "sender_id": 1,
  "content": "안녕하세요!",
  "created_at": "2026-04-15T12:00:00Z"
}
```

### 운영 노트
- 현재 단일 워커(uvicorn `--workers 1`) 인메모리 ConnectionManager. 멀티 워커 확장 시 Redis pub/sub `chat:{room_id}` 채널을 ConnectionManager 내부에서 fan-in/fan-out 하도록 보강할 예정 — REST 라우터는 변경되지 않는다.
- 클라이언트가 보내는 메시지는 모두 무시 (heartbeat/ping 용도). 실제 송신은 REST `POST .../messages`.
- 첫 메시지가 발송되기 전에도 WS 연결은 가능하다(application 이 존재하고 참여자라면). 단, `chat_rooms` 가 아직 없으면 메시지가 아직 broadcast 되지 않는다.

---

## 클라이언트 흐름 권장

1. 매칭 상세에서 `application_id` 를 안 직후 WS 연결.
2. 초기 메시지 로딩은 `GET /matches/{m}/applications/{a}/messages` 사용.
3. 입력은 항상 `POST .../messages` REST 호출. 성공 시 본인 화면은 REST 응답으로 즉시 반영하고, WS 는 상대방 메시지/자기 메시지 모두 수신 (자기 메시지는 sender_id 비교로 중복 표시 회피).
4. 채팅방 진입 시 자동으로 본인이 보낸 게 아닌 메시지가 `read_at` 갱신된다 — `GET .../messages` 호출 자체가 read receipt 역할.

---

## 차단·신고

- 양방향 차단된 상대에게는 메시지 전송 403, 스레드 목록(`GET /matches/{m}/chats`)에서 해당 스레드 비노출, WS 연결 4403.
- 채팅 내 신고는 `POST /reports/chat` 사용 (`report.md` §4.2). `chat_id` = `chat_rooms.id`.
