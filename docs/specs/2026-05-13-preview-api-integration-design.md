# 시흥가개 Preview — API 통합 & 세부 화면 구현 설계

**날짜**: 2026-05-13  
**범위**: `app/static/preview/` 전체 화면 API 연결 + 10개 신규 세부 화면 구현  
**방식**: API-only (정적 fallback 없음, JWT 인증 필수)

---

## 1. 인증 & 세션

- `login.html` → `POST /api/v1/auth/login` → `{ access_token, refresh_token }` → `localStorage` 저장
- 모든 boot 함수 첫 줄: `Auth.requireLogin()` — JWT 없거나 만료 시 `login.html?redirect=<current>` 이동
- 401 응답: `API.call()`이 자동으로 `POST /api/v1/auth/refresh` 시도 → 실패 시 로그아웃 + `login.html`
- 로그인 UI: 전화번호 + 비밀번호 폼. 소셜 로그인 버튼은 placeholder (API 미지원)
- 회원가입 UI: `signup.html` → `POST /api/v1/auth/signup`

---

## 2. 공통 패턴

### 로딩 & 에러
- API 응답 전: `.skeleton` 클래스로 shimmer 효과 표시
- 응답 후: `Bind.render(data)` 로 DOM 덮어쓰기
- 오류 시: Toast("오류가 발생했습니다") + "다시 시도" 버튼

### 페이지 이동 (URL 파라미터)
- `?id=<match_id>` — 상세 화면 ID 전달
- `?pet_id=<pet_id>` — 반려동물 수정 시
- `?application_id=<id>` — 채팅 화면 진입

### preview-app.js 구조 추가
- `Auth.login(phone, password)` — 로그인 처리
- `Auth.signup(data)` — 회원가입 처리
- `bootNews()`, `bootNotifications()`, `bootMatchDetail()`, `bootMatchNew()`, `bootStoreDetail()`, `bootNewsDetail()`, `bootChat()` (확장), `bootProfileEdit()`, `bootPetForm()` — 신규/완성

---

## 3. Phase 1 — 기존 5개 페이지 + 알림 페이지 API 연결

### 3-1. Home (`index.html`)

**API**: `GET /api/v1/home/dashboard` + `GET /api/v1/news?limit=2`

`HomeDashboardResponse` 필드:
- `walk_score` → `.hero-score` (null이면 `--` 표시)
- `weather.temp_c` + `weather.condition` → 날씨 영역
- `nearby_store_count` → "내 주변 N곳" 텍스트
- `my_match_summary.as_author` / `as_applicant` → 매칭 카드 (null이면 숨김)
- `unread_notification_count > 0` → 벨 아이콘 dot 표시
- 뉴스 2개는 별도 `GET /api/v1/news?limit=2` 병렬 요청 → 홈 뉴스 슬롯

### 3-2. Match List (`match.html`)

**API**: `GET /api/v1/matches?status=<filter>`, `GET /api/v1/users/me/activity-stats`

바인딩:
- `activity.review_count` → "검토 중 N건" 카드
- `activity.active_count` → "진행 중 N건" 카드
- `matches[]` → 매칭 카드 목록 (`data-bind-each`)
- 탭 클릭 시 `?status=OPEN|REVIEWING|IN_PROGRESS|COMPLETED` 쿼리로 재조회
- FAB "+" → `match-new.html`

### 3-3. Map (`map.html`)

**API**: `GET /api/v1/maps/stores?lat=<lat>&lng=<lng>&radius=2000`

바인딩:
- KakaoMap SDK 영역 = placeholder div (지도 렌더링 없음)
- 하단 시트 목록: `stores[]` → place-row 항목 (`data-bind-each`)
- 즐겨찾기 버튼: `POST/DELETE /api/v1/favorites/stores/{id}` (토글)
- 카테고리 필터 칩 → `GET /api/v1/maps/stores/filter?category=<cat>` 재조회
- 검색 → `GET /api/v1/maps/stores/search?q=<query>`
- 위치: `navigator.geolocation` — 거부 시 시흥시 중심 좌표 `(37.3797, 126.8027)` 사용

### 3-4. My (`my.html`)

**API**: `GET /api/v1/users/me`, `GET /api/v1/users/me/activity-stats`

바인딩:
- `user.nickname`, `user.profile_image` → 프로필 영역
- `user.pets[]` → `.pets-scroll` 수평 카드 목록
- `stats.match_count`, `stats.volunteer_count` → 통계 칩
- 반려동물 카드 탭 → `profile-edit.html` / `pet-form.html` 이동
- 로그아웃 버튼 → `Auth.logout()` → `login.html`

### 3-5. News (`news.html`)

**API**: `GET /api/v1/news?category=<cat>&limit=20`

바인딩:
- `items[0]` → `.news-feat` 피처드 카드 (og_image → `<img src>`, 없으면 gradient placeholder)
- `items[1..]` → `.news-rows` 목록 (`data-bind-each`)
- 카테고리 칩 → 동일 API 재조회 (`category=EVENT|VOLUNTEER|SUPPORT|POLICY`)
- 아이템 클릭 → `news-detail.html?id=<news_id>`

### 3-6. Notifications (`notifications.html`)

**API**: `GET /api/v1/notifications?type=<filter>`, `PATCH /api/v1/notifications/read-all`

바인딩:
- `notifications[]` → 알림 목록 (`data-bind-each`)
- 읽지 않음 = `.unread` 클래스 조건부 적용
- 아이템 탭 → `POST /api/v1/notifications/{id}/read` + 연관 화면 이동
- "모두 읽음" 버튼 → `PATCH /api/v1/notifications/read-all` → 목록 새로고침
- 필터 칩: `type=MATCH|NEWS|SYSTEM`

---

## 4. Phase 2 — 신규 세부 화면 (10개 파일)

### 4-1. `login.html`
- 전화번호 + 비밀번호 폼
- `POST /api/v1/auth/login` → 토큰 저장 → redirect
- "회원가입" 링크 → `signup.html`

### 4-2. `signup.html`
- 전화번호, 비밀번호, 닉네임 필드
- `POST /api/v1/auth/signup` → 자동 로그인 후 `index.html`

### 4-3. `match-new.html` (3-step wizard, 단일 파일)

3개 스텝을 `.step-panel` 단위로 JS로 전환:

**Step 1 — 반려동물 선택**
- `GET /api/v1/users/me` → `pets[]` 그리드 카드 렌더
- 카드 탭으로 선택, 선택 상태 `.selected` 강조

**Step 2 — 일정 선택**
- 인라인 캘린더 (Vanilla JS, 외부 라이브러리 없음)
- 날짜 선택 후 시간 칩 (09:00 / 12:00 / 15:00 / 18:00 / 직접 입력)

**Step 3 — 요청 내용**
- 제목 (입력), 목적지 (텍스트), 메모 (500자 textarea)
- "완료" → `POST /api/v1/matches` → `match-detail.html?id=<new_id>` 이동

### 4-4. `match-detail.html`

**API**: `GET /api/v1/matches/{id}`, `GET /api/v1/matches/{id}/applications`

**오너 뷰** (본인이 작성한 요청):
- 매칭 정보 헤더 (반려동물 / 날짜 / 목적지 / 상태)
- 신청자 목록: `applications[]` — 이름, 별점, 봉사 횟수
- 신청자 카드 탭 → 수락(`PATCH .../applications/{app_id}` → status: ACCEPTED) / 거절
- 수락 후 "채팅하기" 버튼 → `chat.html?application_id=<id>`
- 완료 후 "후기 작성" 버튼 → 인라인 별점 + 코멘트 폼 (`POST .../review`)

**봉사자 뷰** (본인이 신청한 요청):
- 매칭 정보 + 신청 상태 배지
- 수락된 경우 "채팅하기" 버튼

### 4-5. `my-matches.html`

**API**: `GET /api/v1/users/me/matches?status=<filter>`

- 상태 필터 탭 (전체 / 모집중 / 검토중 / 진행중 / 완료)
- 매칭 카드 목록 → 카드 탭 시 `match-detail.html?id=<id>`
- `my.html`에서 "내 요청" 링크로 진입

### 4-6. `store-detail.html`

**API**: `GET /api/v1/maps/stores/{id}`, `GET /api/v1/maps/stores/{id}/reviews`

- 스토어 이름, 카테고리, 주소, 영업시간, 전화번호
- KakaoMap 소형 지도 = placeholder div
- 즐겨찾기 토글 버튼 (`POST/DELETE /api/v1/favorites/stores/{id}`)
- 리뷰 목록 (`reviews[]`)
- "리뷰 작성" → 별점 + 코멘트 폼 (`POST .../reviews`)
- `map.html` 스토어 카드 탭 시 진입

### 4-7. `news-detail.html`

**API**: `GET /api/v1/news/{news_id}`

- og_image 헤더 이미지 (없으면 gradient)
- 카테고리 배지, 제목, 발행일, 출처
- 본문 (`content` 필드, HTML safe 렌더)
- "원문 보기" 외부 링크 버튼 (`source_url`)
- `news.html` 아이템 탭 시 진입

### 4-8. `chat.html`

**API**:
- `GET /api/v1/matches/{match_id}/applications/{application_id}/messages` — 이력 로드
- `POST /api/v1/matches/{match_id}/applications/{application_id}/messages` — 메시지 전송 (REST fallback)
- `WS /api/v1/ws/applications/{application_id}?token=<JWT>` — 실시간 수신

URL 파라미터: `?match_id=<id>&application_id=<id>` (match-detail.html에서 진입 시 전달)

- 상단: 매칭 요약 정보 바 (반려동물명, 날짜)
- 메시지 목록: 이력 먼저 렌더 → WS 연결 후 실시간 추가
- 입력창 + 전송 버튼 (전송은 REST POST, WS는 수신 전용)
- WS 끊기면 Toast("연결이 끊겼습니다") + 재연결 버튼

### 4-9. `profile-edit.html`

**API**: `GET /api/v1/users/me` (현재값 prefill), `PATCH /api/v1/users/me`

- 닉네임, 자기소개, 프로필 이미지 URL 입력
- "저장" → `PATCH /api/v1/users/me` → Toast + `my.html` 복귀

### 4-10. `pet-form.html`

**API**: `POST /api/v1/pets` (추가) / `PATCH /api/v1/pets/{id}` (수정), `DELETE /api/v1/pets/{id}`

- 이름, 종 (강아지/고양이), 품종, 나이, 성별, 중성화 여부
- `?pet_id=<id>` 쿼리 파라미터 있을 때 수정 모드 (기존값 prefill)
- "삭제" 버튼 (수정 모드만, confirm 다이얼로그 후 `DELETE`)

---

## 5. 파일 목록 요약

| 파일 | 상태 | Phase |
|------|------|-------|
| `index.html` | 수정 | 1 |
| `match.html` | 수정 | 1 |
| `map.html` | 수정 | 1 |
| `my.html` | 수정 | 1 |
| `news.html` | 수정 | 1 |
| `notifications.html` | 수정 | 1 |
| `preview-app.js` | 수정 (boot 함수 추가/완성) | 1+2 |
| `login.html` | 신규 | 2 |
| `signup.html` | 신규 | 2 |
| `match-new.html` | 신규 | 2 |
| `match-detail.html` | 신규 | 2 |
| `my-matches.html` | 신규 | 2 |
| `store-detail.html` | 신규 | 2 |
| `news-detail.html` | 신규 | 2 |
| `chat.html` | 신규 | 2 |
| `profile-edit.html` | 신규 | 2 |
| `pet-form.html` | 신규 | 2 |

---

## 6. 지도 처리 방침

KakaoMap SDK를 사용하는 지도 렌더링 영역(`#mapCanvas`, `store-detail.html` 소형 지도)은 모두 placeholder `<div>` 로 대체한다. 하단 시트의 스토어 목록, 검색, 카테고리 필터, 즐겨찾기 등 나머지 기능은 모두 API에 연결하여 완성한다.

---

## 7. API Base URL

`preview-app.js`의 `API_BASE` 상수 = `/api/v1` (상대 경로). 개발 서버(`localhost:8000`)와 운영 모두 동일하게 동작한다.
