# API 명세서 — 중성화 이동 지원 매칭 (Match)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

> ⚠️ 본 카테고리는 원본 명세에서 API 상세 정의가 누락되어 있어, 아래는 **제안 명세 (TBD)** 이며 담당자 확정 후 갱신 예정.

---

## 3. 중성화 이동 지원 매칭 (Match)

### 3.1 이동 지원 요청 글 작성 — `POST /matches` [T0]
- 인증 필요
- Body(예정): `title`, `content`, `latitude`, `longitude`, `desired_date`, `pet_id`
- Response: 201 Created + 생성된 요청 정보

### 3.2 이동 지원 요청 글 수정 — `PATCH /matches/{match_id}` [T1]
- 인증 필요 / 본인 작성 글만 수정 가능
- Errors: 403 (본인 아님), 404 (없음), 409 (이미 매칭 진행 중)

### 3.3 이동 지원 요청 글 삭제 — `DELETE /matches/{match_id}` [T1]
- 인증 필요 / 본인 작성 글만 삭제 가능 / Response: 204

### 3.4 이동 지원 요청 목록 조회 — `GET /matches` [T0]
- 인증 필요 (봉사자 권한 권장)
- Query(예정): `status`, `region`, `from_date`, `to_date`, `page`, `size`

### 3.5 특정 요청 상세 정보 조회 — `GET /matches/{match_id}` [T0]
- 인증 필요 / Path: `match_id`

### 3.6 봉사 신청하기 — `POST /matches/{match_id}/applications` [T0]
- 인증 필요 (봉사자) / Body(예정): `message`
- Response: 201 + 신청 정보

### 3.7 신청자 목록 조회(작성자용) — `GET /matches/{match_id}/applications` [T0]
- 인증 필요 (요청 작성자만)
- Errors: 403 (작성자 아님)

### 3.8 봉사자 매칭 수락/거절 — `PATCH /matches/{match_id}/applications/{application_id}` [T0]
- 인증 필요 (요청 작성자만)
- Body(예정): `action` (`ACCEPT` / `REJECT`)
- 호출 위치: 신청자 카드의 "거절" 버튼 또는 채팅방 안의 "이 분과 매칭하기" 액션
- 동작: 작성자가 채팅으로 대화 후 결정. `ACCEPT` 시 같은 매칭의 다른 PENDING application은 모두 자동 `REJECTED` 처리되고 `matches.status = 'PROGRESS'`로 전이. 거절된 application의 채팅 스레드는 비활성화(메시지는 보존).
- Response: 매칭 상태 변경 + 양측 알림 발송

### 3.9 매칭 상태 실시간 업데이트 — `PATCH /matches/{match_id}/status` [T1]
- 인증 필요
- Body(예정): `status` (`PROGRESS` / `DONE`)
- WebSocket 채널 `/ws/matches/{match_id}`로 푸시 (구현 검토)

### 3.10 채팅 메시지 발송 — `POST /matches/{match_id}/applications/{application_id}/messages` [T1]
- 인증 필요 (작성자 또는 신청자 본인만 — `application.match.author_id` 또는 `application.applicant_id`)
- 트리거: 신청 발생 직후부터 작성자가 채팅 시작 가능. application.status가 PENDING/ACCEPTED일 때 활성, REJECTED 시 비활성.
- Body(예정): `content` (text)
- Response: 201 Created + 메시지 객체 (`chat_messages.id, content, created_at`)
- WebSocket `/ws/applications/{application_id}`로 실시간 전달

### 3.11 채팅 메시지 조회 — `GET /matches/{match_id}/applications/{application_id}/messages` [T1]
- 인증 필요 (참여자 본인만)
- Query: `before_id` (커서 페이지네이션), `size` (기본 30)
- Response: 메시지 배열 (created_at DESC) + 상대방 마지막 read_at

### 3.12 채팅 스레드 목록 조회 — `GET /matches/{match_id}/chats` [T1]
- 인증 필요 (작성자만 — 자기 매칭의 모든 신청자 스레드 조회)
- Response: 신청자별 스레드 미리보기 배열 (`{ application_id, applicant.nickname, last_message, unread_count, application.status }`)
- 봉사자 시점에서는 자기 application 1건의 스레드만 보이므로 별도 조회 불필요 (`/users/me/chats`로 통합)

### 3.13 봉사 완료 인증 및 후기 작성 — `POST /matches/{match_id}/review` [T1]
- 인증 필요 / Body(예정): `proof_image_urls`, `rating`, `content`

### 3.14 개인별 누적 봉사 이력 통계 — `GET /users/me/volunteer-stats` [T2]
- 인증 필요 (봉사자만)
- Response(예정): `total_count`, `total_hours`, `avg_rating`
