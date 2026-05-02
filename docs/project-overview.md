# 프로젝트 정보 — 시흥가개

> 마지막 갱신: 2026-05-02. 코드 변경에 따라 이 문서를 함께 손봐야 한다.

## 1. 기본 정보

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | 시흥가개 |
| 앱 이름 | 시흥가개 |
| 팀명 | 삼삼오오 (3팀) |
| 과목 | 모바일프로그래밍 2026년 1학기 |
| 플랫폼 | Android (모바일 클라이언트) + REST API 백엔드 |

## 2. 팀 구성

| 이름 | 역할군 |
| --- | --- |
| 김강문 | 백엔드 |
| 이병화 | 백엔드 |
| 김가연 | 백엔드 |
| 김재호 | 앱 제작 담당 |
| 김태은 | 앱 제작 담당 |

> 백엔드 명세 작성은 위 백엔드 인원이 분담했다. 실제 백엔드 구현은 그와 별개로 진행 중이며, 현재 시점 기준 구현 상태는 `feature-spec.md`의 ✅/⚠️/❌ 표기를 따른다.

## 3. 프로젝트 필요성

- 2025년 기준 시흥시의 등록 반려동물 수는 약 5만 마리에 달할 것으로 예상되며, 관련 수요가 빠르게 증가하고 있다.
- 2026년 3월 시행 예정인 강화된 식품위생법 시행규칙으로 인해 반려인들의 혼란이 예상되며, "반려동물 동반 가능 매장" 정보를 신뢰성 있게 제공하는 것이 중요해졌다.
- 시흥시가 추진 중인 **취약계층 실외견 중성화 이동 지원 사업**의 행정적 실효성을 높이기 위해, 자원봉사자 매칭 기능이 필요하다.
- 위 두 축을 결합하여 지역 맞춤형 반려동물 커뮤니티 생태계를 구축한다.

## 4. 프로젝트 개요

시흥시 내 반려동물 출입 가능 매장 정보를 **지도 기반**으로 제공하는 동시에, 취약계층이 키우는 실외견의 중성화 수술 이동을 지원하는 **자원봉사자 매칭** 기능을 핵심 서비스로 삼는 안드로이드 애플리케이션이다. 단순 장소 안내를 넘어 지역 반려동물 복지 향상을 위한 실질적 이동 지원 체계를 구축해 지역사회 문제 해결에 기여하는 것을 목표로 한다.

## 5. 유사 앱 분석 및 차별성

### 시장 내 유사 서비스
- **와요 펫시터**, **멍냥보감** : 반려동물 동반 가능 장소 정보 제공
- **포인핸드** : 유기동물 보호 및 입양 지원

### 한계
기존 서비스는 전국 단위로 방대한 데이터를 다루기 때문에, 특정 지역 정보의 신속한 반영과 실시간 갱신이 어렵다.

### 차별성
- **지역 집중**: 시흥시에 한정된 데이터로 정확성과 최신성 확보
- **복지 매칭 기능**: 취약계층 실외견 중성화 이동 지원을 위한 지역 자원봉사자 매칭 시스템 도입
- **사용자 참여형 데이터**: 이용자 리뷰와 평가를 통해 출입 가능 여부 등 변동이 잦은 매장 정보를 빠르게 공유

## 6. 핵심 기능 (6개 도메인)

| # | 도메인 | 약어 | 핵심 기능 | 라우터 파일 |
| --- | --- | --- | --- | --- |
| 1 | 사용자 관리 | Auth | 회원가입/로그인/JWT, 내 정보, 반려동물, 봉사자 권한 요청·승인 | `auth.py` `users.py` `pets.py` `admin.py` |
| 2 | 알림 | Notification | 알림 목록·미읽음 카운트, FCM 디바이스 토큰 등록 | `notifications.py` |
| 3 | 중성화 이동 지원 매칭 | Match | 요청글 작성·조회, 봉사 신청, 매칭 수락/거절 | `matches.py` |
| 4 | 신고/차단 | Report | 게시글·유저 신고 (게시글·채팅 통합 단일 엔드포인트) | `reports.py` |
| 5 | 지도 / 장소 서비스 | Map | 매장 반경 검색·검색·상세·리뷰·등록·관리, 봉사 위치 노출 | `maps.py` |
| 6 | 반려동물 뉴스 캘린더 | News | 시흥시 반려동물 정책 뉴스(네이버 검색 API 캐싱), 월별 캘린더 | `news.py` |

> 기능별 구현 현황과 우선순위는 `feature-spec.md` 참고.

## 7. 기술 스택 / 컨벤션 (백엔드)

| 항목 | 내용 |
| --- | --- |
| 언어 | Python 3.12 |
| 프레임워크 | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (Async) + GeoAlchemy2 |
| DB | PostgreSQL 16 + PostGIS 3.4 (이미지 `postgis/postgis:16-3.4`) |
| DB 드라이버 | asyncpg |
| 캐시 | Redis 7 (뉴스 응답 캐시 4시간) |
| 마이그레이션 | Alembic 1.13 |
| 인증 | JWT — `python-jose` + `passlib[bcrypt]` |
| Access Token 만료 | 30분 |
| Refresh Token 만료 | 7일 |
| 세션 미들웨어 | Starlette `SessionMiddleware` (sqladmin 로그인용) |
| 관리자 콘솔 | sqladmin 0.18 — `/admin` 경로, ID/PW 환경변수 |
| 모니터링 | prometheus-fastapi-instrumentator → `/metrics` |
| 외부 API | 네이버 검색 API (뉴스), FCM (푸시 — 토큰만 저장, 발송 미구현) |
| 정적/템플릿 | 백엔드 임시 콘솔용 Jinja2 (`/`) |
| API Base Path | `/api/v1` |
| Content-Type | `application/json` |
| 컨테이너 | Docker Compose (api / db / redis 3개 서비스) |

## 8. 우선순위 정의

| 등급 | 의미 |
| --- | --- |
| T0 | MVP 필수 기능 — 1차 출시 전까지 반드시 구현 |
| T1 | 부가 기능 — 안정화 단계에서 구현 |
| T2 | 향후 확장 기능 — 시간 여유 시 구현 |

## 9. 산출물 위치

| 문서 | 경로 | 설명 |
| --- | --- | --- |
| 프로젝트 정보 (본 문서) | `docs/project-overview.md` | 팀·기능 개요·기술 스택 |
| 기능 명세서 | `docs/feature-spec.md` | 도메인별 44개 기능 + 구현 상태 |
| 기능 다이어그램 | `docs/feature-diagram.md` | 마인드맵·역할권한·매칭 라이프사이클 |
| API 명세 (도메인별) | `docs/api-spec/*.md` | 6개 도메인 분할: `auth.md` `notification.md` `match.md` `report.md` `map.md` `news.md` |
| DB 설계 | `docs/db/db-design.md`, `docs/db/schema.sql`, `docs/db/er-diagram.md` | ERD·DDL |
| 파일 트리 | `docs/file-tree.md` | 폴더·파일별 역할 |
| Grafana 대시보드 | `docs/grafana-dashboard.json` | `/metrics` 시각화용 |
| 디자인 시스템 | `../docs_design/` | 색상·간격 토큰 (앱 팀과 공유) |
| 슈퍼파워 스펙 (작업 기록) | `docs/superpowers/specs/*.md` | 도메인별 설계·완성 기록 |

## 10. 빠른 시작

```bash
# 1. 환경변수 준비
cp .env.example .env

# 2. 컨테이너 기동 (api/db/redis)
docker compose up -d --build

# 3. 헬스체크
curl http://localhost:8000/health

# 4. API 문서 / 콘솔
open http://localhost:8000/docs       # Swagger
open http://localhost:8000/redoc      # ReDoc
open http://localhost:8000/admin      # SQLAdmin (관리자 로그인)
open http://localhost:8000/           # 임시 백엔드 콘솔(테스트용)

# 5. 마이그레이션
docker compose exec api alembic revision --autogenerate -m "msg"
docker compose exec api alembic upgrade head
```
