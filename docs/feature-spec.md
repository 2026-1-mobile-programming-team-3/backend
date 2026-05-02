# 기능 명세서 — 시흥가개

> 마지막 갱신: 2026-05-02. 코드와 어긋나면 코드를 정답으로 보고 본 문서를 갱신한다.

본 문서는 시흥가개 백엔드의 전체 기능 목록과 기능별 요구사항을 정리한 명세서이다.
총 **44개 기능**을 6개 도메인으로 구분한다. 우선순위 정의는 `project-overview.md` 8절 참고.

> 학교 프로젝트 시연 범위에 맞춰 운영성 기능(차단)은 제외하고 신고·역할 전환은 최소 형태로 간소화했다. DB 구조는 `db/db-design.md` 참고.

## 0. 구현 상태 표기

| 마크 | 의미 |
| --- | --- |
| ✅ | 라우터·서비스·CRUD가 모두 구현되어 호출 가능 |
| ⚠️ | 코드는 작성됐지만 라우터가 등록되지 않거나 부분 구현 |
| ❌ | 미구현 (라우터/서비스 없음) |

---

## 1. 기능 요약 표

| # | 기능명 | 도메인 | 우선순위 | 상태 | 엔드포인트 |
| --- | --- | --- | --- | --- | --- |
| 1 | 회원가입 | Auth | T0 | ✅ | `POST /auth/signup` |
| 2 | 로그인 | Auth | T0 | ✅ | `POST /auth/login` |
| 3 | 토큰 갱신 | Auth | T0 | ✅ | `POST /auth/refresh` |
| 4 | 로그아웃 | Auth | T0 | ✅ | `POST /auth/logout` |
| 5 | 내 정보 조회 | Auth | T0 | ✅ | `GET /users/me` |
| 6 | 계정 정보 수정 | Auth | T0 | ✅ | `PATCH /users/me` |
| 7 | 비밀번호 변경 | Auth | T1 | ✅ | `PUT /users/me/password` |
| 8 | 계정 탈퇴 | Auth | T1 | ✅ | `DELETE /users/me` |
| 9 | 반려동물 등록 | Auth | T0 | ✅ | `POST /users/me/pets` |
| 10 | 반려동물 수정 | Auth | T1 | ✅ | `PATCH /users/me/pets/{pet_id}` |
| 11 | 반려동물 삭제 | Auth | T1 | ✅ | `DELETE /users/me/pets/{pet_id}` |
| 12 | 봉사자 역할 전환 요청 | Auth | T1 | ✅ | `POST /users/me/volunteer-request` |
| 13 | (관리자) 봉사자 요청 목록 | Auth | T1 | ✅ | `GET /admin/volunteer-requests` |
| 14 | (관리자) 봉사자 요청 승인/거부 | Auth | T1 | ✅ | `PATCH /admin/volunteer-requests/{id}` |
| 15 | 알림 목록 조회 | Notification | T0 | ✅ | `GET /notifications` |
| 16 | 알림 전체 읽음 처리 | Notification | T1 | ❌ | — |
| 17 | 안 읽은 알림 개수 | Notification | T0 | ✅ | `GET /notifications/unread-count` |
| 18 | FCM 디바이스 토큰 등록 | Notification | T0 | ✅ | `POST /notifications/devices` |
| 19 | 이동 지원 요청 글 작성 | Match | T0 | ✅ | `POST /matches` |
| 20 | 이동 지원 요청 글 수정/삭제 | Match | T1 | ❌ | — |
| 21 | 이동 지원 요청 목록 조회 | Match | T0 | ✅ | `GET /matches` |
| 22 | 특정 요청 상세 정보 조회 | Match | T0 | ✅ | `GET /matches/{match_id}` |
| 23 | 봉사 신청하기 | Match | T0 | ✅ | `POST /matches/{match_id}/applications` |
| 24 | 신청자 목록 조회(작성자용) | Match | T0 | ✅ | `GET /matches/{match_id}/applications` |
| 25 | 봉사자 매칭 수락/거절 | Match | T0 | ✅ | `PATCH /matches/{match_id}/applications/{application_id}` |
| 26 | 매칭 상태 업데이트(진행/완료) | Match | T1 | ❌ | — |
| 27 | 1:1 채팅 메시지 전송/조회 | Match | T1 | ❌ | — |
| 28 | 봉사 완료 인증 및 후기 작성 | Match | T1 | ❌ | — |
| 29 | 개인별 누적 봉사 이력 통계 | Match | T2 | ❌ | — |
| 30 | 게시글/후기 신고 등록 | Report | T1 | ✅ | `POST /reports` |
| 31 | 채팅 내 유저 신고 등록 | Report | T1 | ✅ | `POST /reports` (UI 진입점만 다름) |
| 32 | 반려동물 출입 가능 매장 지도 조회 | Map | T0 | ✅ | `GET /maps/stores` |
| 33 | 주변 봉사 위치 표시 | Map | T0 | ✅ | `GET /maps/volunteers` |
| 34 | 매장 상세 정보 조회 | Map | T0 | ✅ | `GET /maps/stores/{store_id}` |
| 35 | 매장 검색 | Map | T1 | ✅ | `GET /maps/stores/search` |
| 36 | 지도 마커 필터링 | Map | T1 | ✅ | `GET /maps/stores/filter` |
| 37 | 신규 매장 정보 등록 | Map | T1 | ✅ | `POST /maps/stores` |
| 38 | 매장 정보 수정/삭제 | Map | T2 | ✅ | `PUT/DELETE /maps/stores/{store_id}` |
| 39 | 매장 리뷰 조회 | Map | T1 | ✅ | `GET /maps/stores/{store_id}/reviews` |
| 40 | 매장 리뷰 작성/삭제 | Map | T2 | ✅ | `POST/DELETE /maps/stores/{store_id}/reviews[/{review_id}]` |
| 41 | 정책 뉴스 목록 조회 | News | T0 | ✅ | `GET /news` |
| 42 | 정책 뉴스 상세 조회 | News | T1 | ✅ | `GET /news/{news_id}` |
| 43 | 월별 정책 일정 캘린더 | News | T1 | ✅ | `GET /news/calendar` |
| 44 | 특정 일자 정책 상세 일정 | News | T2 | ✅ | `GET /news/calendar/daily` |

### 우선순위·구현 분포 (2026-05-02 기준)

| 우선순위 | 전체 | ✅ 완료 | ❌ 미구현 |
| --- | ---: | ---: | ---: |
| T0 | 20 | 20 | 0 |
| T1 | 20 | 15 | 5 |
| T2 | 4 | 3 | 1 |
| **합계** | **44** | **38** | **6** |

도메인별 진행률: Auth 14/14 ✅ · Notification 3/4 · Match 6/11 · Report 2/2 ✅ · Map 9/9 ✅ · News 4/4 ✅.

**T0는 전부 완료.** 미완 6건은 모두 매칭 후속(상태/채팅/후기/통계) + 매칭 글 수정삭제 + 알림 일괄 읽음.

---

## 2. 사용자 관리 (Auth) — 14개 (구현 14/14)

### 2.1 회원가입 [T0 / 하] ✅
- `POST /auth/signup`
- 이메일·비밀번호·닉네임·(선택)연락처를 받아 회원 등록.
- 비밀번호는 8자 이상이며 영문·숫자·특수문자를 모두 포함해야 한다 (`app/core/security.py:validate_password_strength`).
- 정상 처리 시 `201`, 검증 실패 `400`, 이메일 또는 닉네임 중복 시 `409`.

### 2.2 로그인 [T0 / 하] ✅
- `POST /auth/login`
- 이메일/비밀번호를 검증하고 JWT Access Token + Refresh Token 발급.
- Access Token 만료 30분, Refresh Token 만료 7일.
- soft-delete된 계정(`deleted_at IS NOT NULL`)은 `crud_user.get_by_email`에서 걸러져 `401`로 끝난다.

### 2.3 토큰 갱신 [T0 / 하] ✅
- `POST /auth/refresh`
- Refresh Token으로 새 Access Token을 발급한다. 만료/취소된 토큰은 `401`.

### 2.4 로그아웃 [T0 / 하] ✅
- `POST /auth/logout`
- Refresh Token을 `revoked_at`으로 무효화한다. 클라이언트는 로컬 토큰을 함께 삭제.

### 2.5 내 정보 조회 [T0 / 하] ✅
- `GET /users/me`
- 본인 프로필과 등록된 반려동물 목록을 함께 반환 (`selectinload`).

### 2.6 계정 정보 수정 [T0 / 하] ✅
- `PATCH /users/me` — 닉네임/연락처/프로필 이미지 등 부분 수정.

### 2.7 비밀번호 변경 [T1 / 하] ✅
- `PUT /users/me/password` — 현재 비밀번호 검증 후 새 비밀번호로 교체. 회원가입과 동일한 강도 검증.

### 2.8 계정 탈퇴 [T1 / 하] ✅
- `DELETE /users/me` — Soft delete (`users.deleted_at = NOW()`). 비밀번호 재확인 필요. 30일 후 영구 삭제(잡 미구현).

### 2.9 반려동물 등록 [T0 / 하] ✅
- `POST /users/me/pets` — 이름·종류·품종·나이·체중·중성화 여부·사진. 다중 등록 가능.

### 2.10 반려동물 수정 [T1 / 하] ✅
- `PATCH /users/me/pets/{pet_id}` — 본인 소유 검증, 미소유 `403`, 미존재 `404`.

### 2.11 반려동물 삭제 [T1 / 하] ✅
- `DELETE /users/me/pets/{pet_id}` → `204 No Content`.

### 2.12 봉사자 역할 전환 요청 [T1 / 중] ✅
- `POST /users/me/volunteer-request` — 자유 텍스트 한 줄 메시지. 동일 사용자가 PENDING을 동시에 2건 가질 수 없다 (DB 부분 unique index `uniq_volunteer_requests_one_pending`). 이미 VOLUNTEER/ADMIN이면 `409`.

### 2.13 (관리자) 봉사자 요청 목록 [T1 / 중] ✅
- `GET /admin/volunteer-requests?status=PENDING&page=&size=` — 관리자 권한 필요 (`get_current_admin`).

### 2.14 (관리자) 봉사자 요청 승인/거부 [T1 / 중] ✅
- `PATCH /admin/volunteer-requests/{request_id}` (`action=APPROVE|REJECT`).
- 승인 시 사용자 `role`이 `VOLUNTEER`로 전이되고 처리 결과 알림 발송 가정. 이미 처리된 요청은 `409`.

---

## 3. 알림 (Notification) — 4개 (구현 3/4)

### 3.1 알림 목록 조회 [T0 / 하] ✅
- `GET /notifications?is_read=&category=&page=&size=`
- 최신순. 카테고리는 `VOLUNTEER` / `MATCH` / `REVIEW` / `NEWS` / `POLICY` / `SYSTEM`.

### 3.2 알림 전체 읽음 처리 [T1 / 하] ❌
- 라우터·서비스 모두 미작성. 별도 엔드포인트 추가 필요.

### 3.3 안 읽은 알림 개수 [T0 / 중] ✅
- `GET /notifications/unread-count` — 배지용 가벼운 카운트.

### 3.4 FCM 디바이스 토큰 등록 [T0 / 중] ✅
- `POST /notifications/devices` — 한 사용자가 여러 기기 등록 가능. 안드로이드만 지원. `devices.fcm_token`은 unique.

---

## 4. 중성화 이동 지원 매칭 (Match) — 11개 (구현 6/11)

### 4.1 이동 지원 요청 글 작성 [T0 / 하] ✅
- `POST /matches` — 제목·내용·좌표(`latitude`/`longitude`)·희망 일정·반려동물 ID. PostGIS `Geography(POINT, 4326)`에 저장.

### 4.2 요청 글 수정/삭제 [T1 / 하] ❌
- 라우터 미작성. 매칭 진행 전까지만 가능하도록 만들 예정.

### 4.3 요청 목록 조회 [T0 / 중] ✅
- `GET /matches?status=&region=&from_date=&to_date=&page=&size=` — 인증 필요. 정렬 `created_at DESC`.

### 4.4 특정 요청 상세 [T0 / 하] ✅
- `GET /matches/{match_id}` — 작성자/반려동물 요약, 좌표, 신청자 수 포함.

### 4.5 봉사 신청 [T0 / 중] ✅
- `POST /matches/{match_id}/applications` — `(match_id, applicant_id)` unique 제약으로 중복 신청 차단. 작성자 본인이 자기 매칭에 신청은 서비스 레이어에서 거부.

### 4.6 신청자 목록 (작성자용) [T0 / 중] ✅
- `GET /matches/{match_id}/applications` — 매칭 작성자만 (`403` 분기).

### 4.7 매칭 수락/거절 [T0 / 중] ✅
- `PATCH /matches/{match_id}/applications/{application_id}` (`action=ACCEPT|REJECT`).
- 수락 시 다른 PENDING 신청은 자동 REJECTED, 매칭 상태 `MATCHING → PROGRESS`. DB 부분 unique `uniq_match_applications_one_accepted`로 ACCEPTED 1건 강제.

### 4.8 매칭 상태 업데이트(진행/완료) [T1 / 중] ❌
- `PATCH /matches/{match_id}/status` — 미구현. WebSocket은 데모 안정성 위해 채택하지 않고 단순 PATCH로 정의돼 있음.

### 4.9 1:1 채팅 메시지 전송/조회 [T1 / 중] ❌
- 모델(`chat_messages`)만 있음. 라우터·서비스 모두 미작성.

### 4.10 봉사 완료 인증·후기 [T1 / 중] ❌
- 모델(`match_reviews`, `proof_image_urls`)만 있음. 라우터 미작성.

### 4.11 누적 봉사 통계 [T2 / 중] ❌
- 마이페이지 통계 미구현.

---

## 5. 신고 (Report) — 2개 (구현 2/2)

> 차단 기능은 데모 범위 외로 제외했다. 신고는 단일 백엔드 엔드포인트로 통합되어 있다.

### 5.1 게시글/후기 신고 등록 [T1 / 하] ✅
- `POST /reports` — body `target_user_id`, `reason`(1~2000자).
- 본인 신고는 `400`. 대상이 없거나 탈퇴면 `404`. `(reporter_id, target_user_id)` unique 위반은 `409` ("이미 신고한 사용자입니다.").

### 5.2 채팅 내 유저 신고 등록 [T1 / 하] ✅
- 동일하게 `POST /reports`. UI 진입점만 다르고 백엔드는 5.1과 같은 엔드포인트를 호출한다.

---

## 6. 지도 / 장소 서비스 (Map) — 9개 (구현 9/9)

### 6.1 출입 가능 매장 지도 조회 [T0 / 상] ✅
- `GET /maps/stores?lat=&lng=&radius=` — PostGIS `ST_DWithin`. 기본 반경 2,000m, 최대 50km. 거리순 정렬, 최대 200건. 인증 불필요.

### 6.2 주변 봉사 위치 [T0 / 중] ✅
- `GET /maps/volunteers` — `WAITING` 상태 매칭의 좌표만 반환. **봉사자 권한 필요** (`get_current_volunteer`).

### 6.3 매장 상세 정보 [T0 / 하] ✅
- `GET /maps/stores/{store_id}` — 운영시간·사진·평균평점 등.

### 6.4 매장 검색 [T1 / 중] ✅
- `GET /maps/stores/search?keyword=` — 상호명·주소 LIKE.

### 6.5 마커 필터링 [T1 / 중] ✅
- `GET /maps/stores/filter?category=&is_pet_allowed=` — 카테고리(`CAFE`/`RESTAURANT`/`PARK`).

### 6.6 신규 매장 등록 [T1 / 중] ✅
- `POST /maps/stores` — 등록 직후 상태 `PENDING` (관리자 검수 후 노출). 인증 필요.

### 6.7 매장 정보 수정/삭제 [T2 / 하] ✅
- `PUT /maps/stores/{store_id}`, `DELETE /maps/stores/{store_id}` — 본인이 등록한 매장 또는 관리자만 가능. 삭제는 soft-delete (`stores.deleted_at`).

### 6.8 매장 리뷰 조회 [T1 / 하] ✅
- `GET /maps/stores/{store_id}/reviews` — 별점·닉네임·반려동물 출입 가능 여부·작성일.

### 6.9 매장 리뷰 작성/삭제 [T2 / 하] ✅
- `POST /maps/stores/{store_id}/reviews`, `DELETE /maps/stores/{store_id}/reviews/{review_id}`.
- `(store_id, author_id)` unique로 중복 리뷰 차단(`409`).
- 출입 가능 정보 출처는 두 갈래: 관리자 입력(공식) + 사용자 리뷰 체크(현장 확인).

---

## 7. 반려동물 뉴스 캘린더 (News) — 4개 (구현 4/4)

### 7.1 정책 뉴스 목록 조회 [T0 / 하] ✅
- `GET /news` — 네이버 검색 API에서 시흥시 반려동물 정책 뉴스를 조회해 4시간 Redis 캐시(`news:list`)로 제공. 인증 불필요.

### 7.2 정책 뉴스 상세 [T1 / 하] ✅
- `GET /news/{news_id}` — `news_id`는 네이버 link의 sha256 12자 prefix. 본문/요약/원문 링크 반환.

### 7.3 월별 캘린더 [T1 / 중] ✅
- `GET /news/calendar?year=&month=` — `calendar_events` 테이블 기준. 캘린더 뷰의 점(Event)을 위한 일자 목록.

### 7.4 특정 일자 상세 [T2 / 하] ✅
- `GET /news/calendar/daily?date=YYYY-MM-DD` — 해당 날짜의 일정 상세.
