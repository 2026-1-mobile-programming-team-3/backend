# 파일 트리 — 시흥가개 백엔드

> 마지막 갱신: 2026-05-02. 폴더와 파일별 역할을 한눈에. 코드 변경에 맞춰 본 문서를 갱신해야 한다.

기준 디렉터리는 `backend/`. 모든 경로는 이 폴더를 루트로 한 상대 경로다.

---

## 0. 한눈에 보는 트리

```
backend/
├── alembic/                 # DB 마이그레이션
│   ├── env.py
│   ├── versions/
│   │   ├── b71ae8903b66_initial.py
│   │   ├── 28b4d318511b_add_check_constraints_to_pets.py
│   │   └── c1a2b3d4e5f6_seed_stores.py
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 엔트리 (미들웨어/라우터/관리자 콘솔/메트릭)
│   ├── web.py               # 정적/Jinja 템플릿용 라우터 ("/" 임시 콘솔)
│   ├── admin/               # SQLAdmin 관리자 콘솔 ("/admin")
│   │   ├── auth.py          # 관리자 로그인 (세션 기반)
│   │   └── views.py         # 모델별 관리 화면 (UserAdmin 등 14개)
│   ├── api/v1/              # 도메인별 REST 라우터 (URL → 검증 → service)
│   │   ├── __init__.py      # api_router (9개 라우터 include)
│   │   ├── admin.py         # 관리자 전용 (봉사자 요청 처리)
│   │   ├── auth.py          # 회원가입/로그인/토큰/로그아웃
│   │   ├── maps.py          # 지도/매장/리뷰/봉사 위치
│   │   ├── matches.py       # 이동지원 매칭
│   │   ├── news.py          # 뉴스/캘린더
│   │   ├── notifications.py # 알림/디바이스
│   │   ├── pets.py          # 반려동물 CRUD
│   │   ├── reports.py       # 신고 (게시글/채팅 통합)
│   │   ├── users.py         # 내 정보/탈퇴/비밀번호/봉사자 요청
│   │   └── endpoints/       # (현재 비어 있음 — 정리 대상 후보)
│   ├── core/                # 공용 인프라
│   │   ├── config.py        # pydantic-settings, .env 로드
│   │   ├── deps.py          # get_db, get_redis, 인증 의존성 (user/volunteer/admin)
│   │   └── security.py      # 비밀번호 해시/검증, JWT, refresh token
│   ├── crud/                # SQLAlchemy 쿼리 (DB I/O 전용)
│   │   ├── match.py         # 매칭/신청/채팅/후기
│   │   ├── news.py          # calendar_events 조회
│   │   ├── notification.py  # 알림 목록/카운트/디바이스
│   │   ├── pet.py           # 반려동물
│   │   ├── refresh_token.py # refresh token 발급/취소/조회
│   │   ├── report.py        # 신고 INSERT
│   │   ├── store.py         # 매장 반경/검색/필터/리뷰
│   │   ├── user.py          # 회원/조회/soft delete
│   │   ├── volunteer_request.py # 봉사자 역할 전환 요청
│   │   └── __init__.py      # 공용 import 묶음 (user/refresh_token/pet)
│   ├── db/                  # 엔진·세션·베이스
│   │   ├── base.py          # DeclarativeBase
│   │   └── session.py       # async engine + AsyncSession factory + get_db
│   ├── models/              # SQLAlchemy ORM 모델 (1테이블 = 1클래스)
│   │   ├── __init__.py      # 전체 모델/Enum re-export
│   │   ├── enums.py         # UserRole, MatchStatus 등 8개 Enum
│   │   ├── match.py         # Match, MatchApplication, ChatMessage, MatchReview
│   │   ├── news.py          # CalendarEvent
│   │   ├── notification.py  # Notification
│   │   ├── report.py        # Report
│   │   ├── store.py         # Store, StoreReview
│   │   ├── user.py          # User, Device, RefreshToken, Pet
│   │   └── volunteer.py     # VolunteerRequest
│   ├── schemas/             # Pydantic 요청/응답 스키마
│   │   ├── __init__.py      # 공용 import
│   │   ├── admin.py         # 관리자 봉사자 요청 처리
│   │   ├── auth.py          # 회원가입/로그인/토큰/공통 메시지
│   │   ├── match.py         # 매칭/신청/봉사 위치
│   │   ├── news.py          # 뉴스 아이템·캘린더
│   │   ├── notification.py  # 알림/디바이스
│   │   ├── pet.py           # 반려동물 CRUD
│   │   ├── report.py        # 신고 요청/응답
│   │   ├── store.py         # 매장 반경/검색/필터/상세/리뷰
│   │   └── user.py          # 내 정보/탈퇴/비밀번호 변경/봉사자 요청
│   ├── services/            # 비즈니스 로직 (라우터 ↔ crud 사이)
│   │   ├── auth.py          # signup/login/refresh/logout/profile/password/delete
│   │   ├── match.py         # 매칭 도메인 전체 로직
│   │   ├── news.py          # 네이버 뉴스 호출 + Redis 캐시 + 캘린더
│   │   ├── notification.py  # 알림 목록/카운트/디바이스
│   │   ├── pet.py           # 반려동물 검증·소유 확인
│   │   ├── report.py        # 신고 검증·중복 차단
│   │   ├── store.py         # 매장/리뷰 비즈니스 규칙
│   │   └── volunteer.py     # 봉사자 요청 승인/거부
│   ├── static/              # 임시 콘솔 정적 자원
│   │   ├── css/main.css
│   │   └── js/api.js        # 콘솔에서 백엔드 호출하는 JS
│   └── templates/           # Jinja2 템플릿
│       ├── base.html        # 공통 레이아웃 + 네비
│       └── index.html       # 백엔드 임시 콘솔 (탭별 API 테스트)
├── docker-compose.yml       # api / db (postgis) / redis 3 서비스
├── Dockerfile               # python:3.12-slim 기반
├── requirements.txt
├── README.md                # 한 줄 설명만 있음
├── docs/                    # 본 문서들
│   ├── api-spec/            # 도메인별 API 명세 (분할)
│   │   ├── auth.md
│   │   ├── map.md
│   │   ├── match.md
│   │   ├── news.md
│   │   ├── notification.md
│   │   └── report.md
│   ├── db/
│   │   ├── db-design.md     # 테이블·관계 설계서
│   │   ├── er-diagram.md    # mermaid ERD
│   │   └── schema.sql       # DDL 원본
│   ├── feature-diagram.md   # 마인드맵·역할권한·매칭 라이프사이클
│   ├── feature-spec.md      # 44개 기능 명세 + 구현 상태
│   ├── file-tree.md         # 본 파일
│   ├── project-overview.md  # 프로젝트 개요·기술 스택·산출물 위치
│   ├── grafana-dashboard.json # /metrics 시각화용
│   ├── siheung.png
│   └── superpowers/specs/   # 도메인별 작업 설계 기록 (history)
├── docs_design/             # 디자인 토큰 (앱 팀과 공유)
└── (.env / .env.example / .gitignore)
```

---

## 1. 루트 파일

| 파일 | 역할 |
| --- | --- |
| `Dockerfile` | `python:3.12-slim` 기반. `requirements.txt` 설치 후 alembic 마이그레이션 → uvicorn 기동. |
| `docker-compose.yml` | `api` / `db (postgis/postgis:16-3.4)` / `redis (7-alpine)` 3개 서비스. db·redis 헬스체크 후 api 기동. |
| `requirements.txt` | FastAPI 0.115, SQLAlchemy 2.0, asyncpg, alembic, redis, sqladmin, prometheus instrumentator, geoalchemy2 등 핵심 의존성. |
| `alembic.ini` | alembic 설정. `sqlalchemy.url`은 placeholder이고 실제 URL은 `alembic/env.py`에서 pydantic settings로 주입. |
| `README.md` | 한 줄 ("백엔드 (REST API)"). 실질 정보는 `docs/`에. |
| `.env` / `.env.example` | DB·Redis·JWT·관리자·네이버 API 자격증명. `.env`는 git ignore. |

---

## 2. `alembic/` — 마이그레이션

| 파일 | 설명 |
| --- | --- |
| `env.py` | 비동기 엔진으로 마이그레이션 실행. `app.models.*`를 import해 `Base.metadata`에 모든 테이블을 등록. PostGIS의 시스템 테이블(`tiger`, `topology` 등)은 `include_object`에서 제외. |
| `versions/b71ae8903b66_initial.py` | 초기 스키마(15테이블 + 모든 Enum/PostGIS 인덱스). 2026-04-28. |
| `versions/28b4d318511b_add_check_constraints_to_pets.py` | `pets.age >= 0`, `weight_kg > 0` 체크 제약 추가. 2026-04-29. |
| `versions/c1a2b3d4e5f6_seed_stores.py` | 데모용 매장 시드 데이터. 2026-05-02. |

새 마이그레이션은 컨테이너 안에서 `alembic revision --autogenerate -m "..."` 후 `alembic upgrade head`.

---

## 3. `app/` — 애플리케이션 코드

### 3.1 진입점

| 파일 | 책임 |
| --- | --- |
| `app/main.py` | `FastAPI()` 인스턴스 생성. CORS·SessionMiddleware 등록 → 정적 파일 mount → `api_router`(`/api/v1`)와 `web_router` include → SQLAdmin(`/admin`) 등록 → Prometheus instrumentator로 `/metrics` 노출 → `/health`, `/api/v1/ping` 정의. |
| `app/web.py` | `"/"` 한 개. `templates/index.html`을 렌더해 임시 콘솔을 노출. OpenAPI에는 `include_in_schema=False`로 숨김. |

### 3.2 `app/api/v1/` — 라우터

URL 라우팅과 의존성(인증·DB) 주입만 담당하고, 비즈니스 로직은 `services/`로 위임한다.

| 파일 | prefix · tags | 엔드포인트 수 | 비고 |
| --- | --- | ---: | --- |
| `__init__.py` | — | — | `api_router`에 9개 라우터 include. |
| `auth.py` | `/auth` · auth | 4 | signup/login/refresh/logout |
| `users.py` | `/users` · users | 5 | 내 정보/수정/비밀번호/탈퇴/봉사자 요청 |
| `pets.py` | `/users/me/pets` · pets | 3 | CRUD |
| `news.py` | `/news` · News | 4 | 뉴스 목록·상세, 캘린더 월·일 |
| `maps.py` | `/maps` · Maps | 11 | 매장 반경/검색/필터/상세/등록/수정/삭제, 리뷰 조회·작성·삭제, 봉사 위치 |
| `matches.py` | `/matches` · Matches | 6 | 작성/목록/상세 + 신청 생성·조회·수락거절 |
| `notifications.py` | `/notifications` · Notifications | 3 | 목록/미읽음 카운트/디바이스 등록 |
| `reports.py` | `/reports` · Reports | 1 | 게시글·채팅 신고 통합 |
| `admin.py` | `/admin` · Admin | 2 | 관리자 봉사자 요청 목록·처리 |
| `endpoints/` | — | — | 빈 폴더 (사용 안 함). 정리 대상 후보. |

### 3.3 `app/services/` — 비즈니스 로직

라우터에서 받은 입력을 검증·조립하고 `crud/`를 호출해 DB I/O를 수행한다.

| 파일 | 핵심 함수 |
| --- | --- |
| `auth.py` | `signup`, `login`(JWT 발급), `refresh`, `logout`, `update_profile`, `change_password`, `delete_account`(soft-delete) |
| `pet.py` | `create_pet`, `update_pet`, `delete_pet` (본인 소유 검증) |
| `volunteer.py` | `list_admin_requests`, `process_admin_request`(APPROVE 시 user role을 VOLUNTEER로 전이) |
| `match.py` | 매칭 도메인 전체 — 작성/목록/상세, 신청 생성, 신청자 목록, 수락·거절(다른 PENDING 자동 REJECTED) |
| `store.py` | 매장 반경 검색(PostGIS `ST_DWithin`), 검색·필터·상세·등록·수정·삭제(soft), 리뷰 조회·작성·삭제, 평점 평균 갱신 |
| `news.py` | 네이버 뉴스 API 호출 → HTML 정제 → Redis 4시간 캐시. 캘린더 월별·일별 조회 |
| `notification.py` | 알림 목록·미읽음 카운트·FCM 디바이스 등록 |
| `report.py` | 신고 생성 — 본인 신고 차단(400), 대상 미존재(404), 중복 신고(409) |

### 3.4 `app/crud/` — DB I/O

SQLAlchemy 쿼리만 담는다. HTTP 예외나 비즈니스 검증은 하지 않는다.

| 파일 | 다루는 모델 |
| --- | --- |
| `user.py` | `User` — 이메일 조회는 `deleted_at IS NULL` 필터. `soft_delete()` 정의. |
| `pet.py` | `Pet` — 본인 소유 조회·CRUD |
| `refresh_token.py` | `RefreshToken` — 발급/조회/취소(`revoked_at`) |
| `volunteer_request.py` | `VolunteerRequest` — PENDING 단일성 보장 |
| `match.py` | `Match`, `MatchApplication` — `WAITING` 매칭 좌표 200건, 신청자 ↔ 작성자 조인 등 |
| `store.py` | `Store`, `StoreReview` — `ST_DWithin`, `LIKE` 검색, 평점 집계 |
| `news.py` | `CalendarEvent` — 월별/일별 일정 |
| `notification.py` | `Notification`, `Device` |
| `report.py` | `Report` — 단순 INSERT (중복은 DB unique 위반 → IntegrityError) |

### 3.5 `app/models/` — ORM 모델

도메인별로 파일 분리. 모든 모델은 `app/db/base.Base`를 상속한다.

| 파일 | 클래스 | 핵심 컬럼·제약 |
| --- | --- | --- |
| `enums.py` | `UserRole`, `PetSpecies`, `NotificationCategory`, `MatchStatus`, `ApplicationStatus`, `VolunteerRequestStatus`, `StoreCategory`, `StoreStatus` | PostgreSQL `Enum` 타입의 1:1 대응 |
| `user.py` | `User`, `Device`, `RefreshToken`, `Pet` | `users.deleted_at`, `pets.is_neutered`, 부분 인덱스 `idx_users_role_active` |
| `match.py` | `Match`, `MatchApplication`, `ChatMessage`, `MatchReview` | `matches.location` PostGIS GIST, `(match_id, applicant_id)` unique, ACCEPTED 1건만 허용하는 부분 unique |
| `store.py` | `Store`, `StoreReview` | `stores.location` PostGIS GIST, `(store_id, author_id)` unique, 평점 평균 캐시 |
| `notification.py` | `Notification` | 미읽음 알림용 부분 인덱스 |
| `news.py` | `CalendarEvent` | `end_date >= start_date` 체크 |
| `report.py` | `Report` | `(reporter_id, target_user_id)` unique로 중복 신고 차단 |
| `volunteer.py` | `VolunteerRequest` | PENDING 1건만 허용하는 부분 unique |
| `__init__.py` | (re-export) | 모든 모델·Enum 한 번에 import 가능 |

### 3.6 `app/schemas/` — Pydantic 모델

요청 본문·응답 모델. 도메인 단위로 분리. 라우터 시그니처는 모두 이 모듈의 클래스를 사용한다.

| 파일 | 주요 클래스 |
| --- | --- |
| `auth.py` | `SignupRequest`, `LoginRequest/Response`, `TokenRefreshRequest/Response`, `LogoutRequest`, `MessageResponse`, 비밀번호 강도 검증 적용 |
| `user.py` | `UserResponse`, `UserMeResponse`(반려동물 포함), `UserUpdateRequest`, `PasswordChangeRequest`, `AccountDeleteRequest`, `VolunteerRequestCreate/Response` |
| `pet.py` | `PetCreate/Update/Response` |
| `notification.py` | `NotificationListResponse`, `UnreadCountResponse`, `DeviceRegisterRequest/Response` |
| `match.py` | `MatchCreate/Detail/List` 계열, `Application*` 계열, `VolunteerLocationItem/ListResponse` |
| `store.py` | `StoreCreate/Update`, `StoreNearby/Search/Filter/Detail` 응답, `StoreReviewCreate/List/Created` |
| `news.py` | `NewsItem/List/Detail`, `CalendarEventOut`, `DailyEventOut`, `CalendarMonthResponse`, `DailyEventsResponse` |
| `report.py` | `ReportCreateRequest/CreatedResponse` |
| `admin.py` | `VolunteerRequestActionRequest`, `VolunteerRequestList/Processed Response` |

### 3.7 `app/core/` — 공용 인프라

| 파일 | 책임 |
| --- | --- |
| `config.py` | pydantic-settings로 `.env` 로드. `DATABASE_URL`은 `postgresql://` → `postgresql+asyncpg://`로 자동 보정. JWT/관리자/네이버 API 자격증명도 여기서. |
| `security.py` | bcrypt 해시·검증, JWT access token encode/decode, refresh token 생성·해시(SHA-256), 비밀번호 강도 검증(`validate_password_strength`). |
| `deps.py` | `get_redis()`, `get_db` (re-export), `get_current_user` (JWT 검증 + soft-delete 가드), `get_current_volunteer`, `get_current_admin` 권한 의존성. |

### 3.8 `app/db/` — DB 인프라

| 파일 | 책임 |
| --- | --- |
| `base.py` | `Base = DeclarativeBase`. 모든 모델의 부모. |
| `session.py` | `engine` (async, `pool_pre_ping=True`), `AsyncSessionLocal`, `get_db()` 의존성. |

### 3.9 `app/admin/` — SQLAdmin 콘솔

| 파일 | 책임 |
| --- | --- |
| `auth.py` | sqladmin `AuthenticationBackend` 구현. 환경변수 `ADMIN_USERNAME` / `ADMIN_PASSWORD`로 세션 로그인. |
| `views.py` | 모델별 `ModelView` 14개(User, Device, RefreshToken, Pet, Notification, Match, MatchApplication, ChatMessage, MatchReview, Store, StoreReview, VolunteerRequest, Report, CalendarEvent). PostGIS Geography·ARRAY 컬럼은 form에서 제외. |

### 3.10 `app/static/` & `app/templates/` — 임시 콘솔

| 파일 | 설명 |
| --- | --- |
| `templates/base.html` | 공통 레이아웃. Swagger·ReDoc·헬스체크 링크. |
| `templates/index.html` | 도메인별 탭(Auth/Users/Pets/Match/Map/News/Notification/Admin)에서 백엔드를 직접 호출하는 콘솔. localStorage에 토큰 보관. |
| `static/css/main.css` | 콘솔 스타일. |
| `static/js/api.js` | fetch 래퍼·세션·탭 전환 로직. |

> 임시 콘솔은 앱 팀이 안드로이드 클라이언트를 완성하기 전까지 백엔드 동작을 확인하는 용도. 운영 시점에는 제거 가능.

---

## 4. `docs/` — 문서

| 파일/폴더 | 설명 |
| --- | --- |
| `project-overview.md` | 프로젝트 개요·팀·기술 스택·산출물 위치. 본인 진입점. |
| `feature-spec.md` | 6개 도메인 44개 기능 명세 + 구현 상태(✅/⚠️/❌). |
| `feature-diagram.md` | 마인드맵·구현 상태 매트릭스·역할권한·매칭 라이프사이클·ERD. |
| `file-tree.md` | 본 문서. |
| `api-spec/` | 도메인별 REST 엔드포인트 명세(`auth.md` `notification.md` `match.md` `report.md` `map.md` `news.md`). |
| `db/db-design.md` | 테이블별 설계 의사결정. |
| `db/schema.sql` | 표준 SQL DDL 스냅샷 (Alembic이 정답). |
| `db/er-diagram.md` | mermaid ERD. |
| `grafana-dashboard.json` | `/metrics` 시각화용 import 파일. |
| `siheung.png` | README/문서용 이미지. |
| `superpowers/specs/*.md` | 도메인별 작업 설계·완성 기록 (history). 새 기능을 더할 때 의사결정 맥락을 참고. |

---

## 5. `docs_design/` (참고)

앱 팀과 공유하는 디자인 시스템 — 색상·텍스트·간격 토큰. 백엔드 코드와는 독립이며, 본 백엔드 문서는 직접 의존하지 않는다.

---

## 6. 정리·갱신 가이드

코드를 바꾸면 다음 문서들을 함께 손봐야 한다.

| 코드 변경 | 함께 갱신할 문서 |
| --- | --- |
| 새 라우터/엔드포인트 추가 | `api-spec/<도메인>.md`, `feature-spec.md` 표, 본 `file-tree.md` |
| 새 도메인 추가 | 위 + `project-overview.md` 6절, `feature-diagram.md` 마인드맵 |
| 모델 추가/변경 | `db/db-design.md`, `db/schema.sql`, `feature-diagram.md` ERD |
| 의존성/스택 변경 | `project-overview.md` 7절, `requirements.txt`, `Dockerfile` |
| 설정/환경변수 추가 | `app/core/config.py`, `.env.example`, `project-overview.md` |

> 본 트리는 정적 스냅샷이다. 코드와 어긋나면 코드를 정답으로 보고 본 문서를 갱신하라.
