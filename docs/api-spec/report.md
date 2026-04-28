# API 명세서 — 신고/차단 (Report)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

> ⚠️ 본 카테고리도 원본 명세에서 API 상세가 누락되어 있어, 아래는 **제안 명세 (TBD)**.

---

## 4. 신고/차단 (Report)

### 4.1 게시글/후기 신고 등록 — `POST /reports` [T1]
- 인증 필요
- Body(예정): `target_type` (`POST` / `REVIEW`), `target_id`, `reason`, `description`
- Errors: 409 (동일 콘텐츠 중복 신고)

### 4.2 채팅 내 유저 신고 등록 — `POST /reports/chat` [T1]
- 인증 필요
- Body(예정): `chat_id`, `target_user_id`, `message_id`, `reason`

### 4.3 특정 사용자 차단 등록 — `POST /users/me/blocks` [T2]
- 인증 필요 / Body(예정): `target_user_id`

### 4.4 차단 사용자 목록 조회 — `GET /users/me/blocks` [T2]
- 인증 필요

### 4.5 차단 해제 — `DELETE /users/me/blocks/{block_id}` [T2]
- 인증 필요 / Response: 204
