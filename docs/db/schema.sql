-- =============================================================================
-- 시흥가개 DB Schema
-- PostgreSQL 16 / PostGIS 3.x
--
-- 자세한 설계 근거는 같은 폴더의 db-design.md 참조.
-- 테이블 우선순위: T0 (MVP) → T1 (안정화) → T2 (확장)
--
-- 모든 테이블·컬럼에 COMMENT ON 으로 한글 설명을 부여한다.
-- (dbdiagram.io 임포트 시 컬럼 노트로 변환되어 다이어그램에서 확인 가능)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. EXTENSIONS
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS postgis;


-- -----------------------------------------------------------------------------
-- 1. ENUM TYPES
-- -----------------------------------------------------------------------------
CREATE TYPE user_role                AS ENUM ('USER', 'VOLUNTEER', 'ADMIN');
CREATE TYPE pet_species              AS ENUM ('DOG', 'CAT', 'OTHER');
CREATE TYPE notification_category    AS ENUM ('VOLUNTEER', 'MATCH', 'REVIEW', 'NEWS', 'POLICY', 'SYSTEM');
CREATE TYPE match_status             AS ENUM ('WAITING', 'MATCHING', 'PROGRESS', 'DONE');
CREATE TYPE application_status       AS ENUM ('PENDING', 'ACCEPTED', 'REJECTED');
CREATE TYPE volunteer_request_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
CREATE TYPE store_category           AS ENUM ('CAFE', 'RESTAURANT', 'PARK');
CREATE TYPE store_status             AS ENUM ('PENDING', 'APPROVED', 'REJECTED');


-- =============================================================================
-- T0 — MVP 필수 테이블
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1.1 users
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id                 BIGSERIAL       PRIMARY KEY,
    email              VARCHAR(255)    NOT NULL UNIQUE,
    password_hash      VARCHAR(255)    NOT NULL,
    nickname           VARCHAR(20)     NOT NULL UNIQUE,
    phone              VARCHAR(20),
    role               user_role       NOT NULL DEFAULT 'USER',
    profile_image_url  TEXT,
    created_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at         TIMESTAMPTZ
);

CREATE INDEX idx_users_role_active
    ON users (role)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE  users                      IS '회원 (USER / VOLUNTEER / ADMIN)';
COMMENT ON COLUMN users.id                   IS '사용자 고유 ID';
COMMENT ON COLUMN users.email                IS '로그인 ID (이메일, 유일값)';
COMMENT ON COLUMN users.password_hash        IS '비밀번호 해시 (bcrypt 또는 argon2)';
COMMENT ON COLUMN users.nickname             IS '닉네임 (2~20자, 유일값)';
COMMENT ON COLUMN users.phone                IS '연락처 (선택)';
COMMENT ON COLUMN users.role                 IS '권한 등급 (USER/VOLUNTEER/ADMIN)';
COMMENT ON COLUMN users.profile_image_url    IS '프로필 이미지 URL (외부 스토리지)';
COMMENT ON COLUMN users.created_at           IS '가입 시각';
COMMENT ON COLUMN users.updated_at           IS '정보 수정 시각';
COMMENT ON COLUMN users.deleted_at           IS '탈퇴 시각 (soft delete, 30일 후 영구 삭제)';


-- -----------------------------------------------------------------------------
-- 1.2 devices  (FCM 디바이스)
-- -----------------------------------------------------------------------------
CREATE TABLE devices (
    id           BIGSERIAL    PRIMARY KEY,
    user_id      BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fcm_token    TEXT         NOT NULL UNIQUE,
    device_name  VARCHAR(100),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_devices_user_id ON devices (user_id);

COMMENT ON TABLE  devices              IS 'FCM 푸시 알림 대상 디바이스 (한 사용자가 여러 기기 가능)';
COMMENT ON COLUMN devices.id           IS '디바이스 레코드 ID';
COMMENT ON COLUMN devices.user_id      IS '소유 사용자 FK';
COMMENT ON COLUMN devices.fcm_token    IS 'Firebase Cloud Messaging 등록 토큰';
COMMENT ON COLUMN devices.device_name  IS '기기명 (디버깅용, 선택)';
COMMENT ON COLUMN devices.created_at   IS '최초 등록 시각';
COMMENT ON COLUMN devices.updated_at   IS '토큰 갱신 시각';


-- -----------------------------------------------------------------------------
-- 1.3 refresh_tokens
-- -----------------------------------------------------------------------------
CREATE TABLE refresh_tokens (
    id          BIGSERIAL     PRIMARY KEY,
    user_id     BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id   BIGINT        REFERENCES devices(id) ON DELETE SET NULL,
    token_hash  VARCHAR(64)   NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ   NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_active
    ON refresh_tokens (user_id)
    WHERE revoked_at IS NULL;

COMMENT ON TABLE  refresh_tokens             IS '활성 리프레시 토큰 화이트리스트 (멀티 디바이스 로그인)';
COMMENT ON COLUMN refresh_tokens.id          IS '토큰 레코드 ID';
COMMENT ON COLUMN refresh_tokens.user_id     IS '소유 사용자 FK';
COMMENT ON COLUMN refresh_tokens.device_id   IS '발급된 디바이스 FK (선택)';
COMMENT ON COLUMN refresh_tokens.token_hash  IS 'raw refresh token 의 SHA-256 hex 해시 (64자, 원문 미저장)';
COMMENT ON COLUMN refresh_tokens.expires_at  IS '만료 시각 (발급 + 7일)';
COMMENT ON COLUMN refresh_tokens.revoked_at  IS '무효화 시각 (로그아웃 시 set)';
COMMENT ON COLUMN refresh_tokens.created_at  IS '발급 시각';


-- -----------------------------------------------------------------------------
-- 1.4 pets
-- -----------------------------------------------------------------------------
CREATE TABLE pets (
    id           BIGSERIAL     PRIMARY KEY,
    user_id      BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         VARCHAR(50)   NOT NULL,
    species      pet_species   NOT NULL,
    breed        VARCHAR(50),
    age          SMALLINT      CHECK (age IS NULL OR age >= 0),
    weight_kg    NUMERIC(5,2)  CHECK (weight_kg IS NULL OR weight_kg > 0),
    is_neutered  BOOLEAN       NOT NULL DEFAULT FALSE,
    photo_url    TEXT,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pets_user_id ON pets (user_id);

COMMENT ON TABLE  pets              IS '회원이 등록한 반려동물';
COMMENT ON COLUMN pets.id           IS '반려동물 ID';
COMMENT ON COLUMN pets.user_id      IS '보호자(회원) FK';
COMMENT ON COLUMN pets.name         IS '이름';
COMMENT ON COLUMN pets.species      IS '종 (DOG/CAT/OTHER)';
COMMENT ON COLUMN pets.breed        IS '품종 (선택)';
COMMENT ON COLUMN pets.age          IS '나이 (>= 0, 선택)';
COMMENT ON COLUMN pets.weight_kg    IS '체중 kg (> 0, 선택)';
COMMENT ON COLUMN pets.is_neutered  IS '중성화 여부';
COMMENT ON COLUMN pets.photo_url    IS '사진 URL (외부 스토리지)';
COMMENT ON COLUMN pets.created_at   IS '등록 시각';
COMMENT ON COLUMN pets.updated_at   IS '정보 수정 시각';


-- -----------------------------------------------------------------------------
-- 1.5 notifications
-- -----------------------------------------------------------------------------
CREATE TABLE notifications (
    id          BIGSERIAL              PRIMARY KEY,
    user_id     BIGINT                 NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category    notification_category  NOT NULL,
    title       VARCHAR(100)           NOT NULL,
    body        TEXT                   NOT NULL,
    link        VARCHAR(255),
    read_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ            NOT NULL DEFAULT NOW()
);

-- 일반 알림 목록 (최신순)
CREATE INDEX idx_notifications_user_created
    ON notifications (user_id, created_at DESC);

-- 안읽음 카운트/목록 — read_at IS NULL 부분 인덱스
CREATE INDEX idx_notifications_user_unread
    ON notifications (user_id, created_at DESC)
    WHERE read_at IS NULL;

COMMENT ON TABLE  notifications             IS '인앱 알림 (FCM 발송과 별개로 목록/배지 표시에 사용)';
COMMENT ON COLUMN notifications.id          IS '알림 ID';
COMMENT ON COLUMN notifications.user_id     IS '수신자 FK';
COMMENT ON COLUMN notifications.category    IS '분류 (VOLUNTEER/MATCH/REVIEW/NEWS/POLICY/SYSTEM)';
COMMENT ON COLUMN notifications.title       IS '알림 제목';
COMMENT ON COLUMN notifications.body        IS '알림 본문';
COMMENT ON COLUMN notifications.link        IS '클릭 시 이동할 in-app deep link 경로 (예: /match/42)';
COMMENT ON COLUMN notifications.read_at     IS '읽은 시각 (NULL = 안 읽음, 안읽음 카운트는 read_at IS NULL 조건으로 조회)';
COMMENT ON COLUMN notifications.created_at  IS '생성 시각';


-- -----------------------------------------------------------------------------
-- 1.6 matches  (이동 지원 요청 글)
-- -----------------------------------------------------------------------------
CREATE TABLE matches (
    id            BIGSERIAL                  PRIMARY KEY,
    author_id     BIGINT                     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pet_id        BIGINT                     REFERENCES pets(id) ON DELETE SET NULL,
    title         VARCHAR(100)               NOT NULL,
    content       TEXT                       NOT NULL,
    location      GEOGRAPHY(POINT, 4326)     NOT NULL,
    address       VARCHAR(255),
    desired_date  DATE,
    status        match_status               NOT NULL DEFAULT 'WAITING',
    created_at    TIMESTAMPTZ                NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ                NOT NULL DEFAULT NOW(),
    deleted_at    TIMESTAMPTZ
);

CREATE INDEX idx_matches_status_created
    ON matches (status, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_matches_location_gist
    ON matches USING GIST (location);

COMMENT ON TABLE  matches               IS '이동 지원 요청 글 (작성 + 매칭 진행 상태 통합)';
COMMENT ON COLUMN matches.id            IS '요청 글 ID';
COMMENT ON COLUMN matches.author_id     IS '작성자 (보호자) FK';
COMMENT ON COLUMN matches.pet_id        IS '대상 반려동물 FK';
COMMENT ON COLUMN matches.title         IS '제목';
COMMENT ON COLUMN matches.content       IS '본문';
COMMENT ON COLUMN matches.location      IS '출발/픽업 좌표 (PostGIS Point, SRID 4326)';
COMMENT ON COLUMN matches.address       IS '사람이 읽는 주소';
COMMENT ON COLUMN matches.desired_date  IS '희망 일정';
COMMENT ON COLUMN matches.status        IS '진행 상태 (WAITING → MATCHING → PROGRESS → DONE)';
COMMENT ON COLUMN matches.created_at    IS '작성 시각';
COMMENT ON COLUMN matches.updated_at    IS '수정 시각';
COMMENT ON COLUMN matches.deleted_at    IS '삭제 시각 (soft delete)';


-- -----------------------------------------------------------------------------
-- 1.7 match_applications
-- -----------------------------------------------------------------------------
CREATE TABLE match_applications (
    id            BIGSERIAL           PRIMARY KEY,
    match_id      BIGINT              NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    applicant_id  BIGINT              NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    message       TEXT,
    status        application_status  NOT NULL DEFAULT 'PENDING',
    created_at    TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, applicant_id)
);

-- 한 매칭당 ACCEPTED 신청자는 1명만 가능 (DB 레벨 보장)
CREATE UNIQUE INDEX uniq_match_applications_one_accepted
    ON match_applications (match_id)
    WHERE status = 'ACCEPTED';

CREATE INDEX idx_match_applications_match_status
    ON match_applications (match_id, status);

COMMENT ON TABLE  match_applications              IS '봉사 신청 (작성자가 ACCEPT 시 매칭 성사)';
COMMENT ON COLUMN match_applications.id           IS '신청 ID';
COMMENT ON COLUMN match_applications.match_id     IS '대상 매칭 글 FK';
COMMENT ON COLUMN match_applications.applicant_id IS '신청 봉사자 FK';
COMMENT ON COLUMN match_applications.message      IS '신청 메시지 (자유 텍스트)';
COMMENT ON COLUMN match_applications.status       IS '신청 상태 (PENDING/ACCEPTED/REJECTED)';
COMMENT ON COLUMN match_applications.created_at   IS '신청 시각';
COMMENT ON COLUMN match_applications.updated_at   IS '상태 변경 시각';


-- -----------------------------------------------------------------------------
-- 1.8 stores
-- -----------------------------------------------------------------------------
CREATE TABLE stores (
    id               BIGSERIAL                PRIMARY KEY,
    name             VARCHAR(100)             NOT NULL,
    address          VARCHAR(255)             NOT NULL,
    phone            VARCHAR(20),
    category         store_category           NOT NULL,
    location         GEOGRAPHY(POINT, 4326)   NOT NULL,
    operating_hours  VARCHAR(100),
    photo_urls       TEXT[]                   NOT NULL DEFAULT '{}',
    is_pet_allowed   BOOLEAN                  NOT NULL DEFAULT TRUE,
    status           store_status             NOT NULL DEFAULT 'PENDING',
    created_by       BIGINT                   REFERENCES users(id) ON DELETE SET NULL,
    rating_avg       NUMERIC(3,2)             NOT NULL DEFAULT 0,
    rating_count     INTEGER                  NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ              NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ              NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX idx_stores_location_gist
    ON stores USING GIST (location);

CREATE INDEX idx_stores_status_category
    ON stores (status, category)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE  stores                  IS '반려동물 동반 가능 매장';
COMMENT ON COLUMN stores.id               IS '매장 ID';
COMMENT ON COLUMN stores.name             IS '상호명';
COMMENT ON COLUMN stores.address          IS '주소';
COMMENT ON COLUMN stores.phone            IS '전화번호';
COMMENT ON COLUMN stores.category         IS '분류 (CAFE/RESTAURANT/PARK)';
COMMENT ON COLUMN stores.location         IS '좌표 (PostGIS Point, SRID 4326)';
COMMENT ON COLUMN stores.operating_hours  IS '운영 시간 자유 문자열 (예: 10:00-22:00)';
COMMENT ON COLUMN stores.photo_urls       IS '매장 사진 URL 배열 (외부 스토리지, 배열 순서 = 표시 순서)';
COMMENT ON COLUMN stores.is_pet_allowed   IS '반려동물 출입 가능 여부 (관리자/시드 입력 - 공식 정보. 사용자 확인은 store_reviews.is_pet_allowed)';
COMMENT ON COLUMN stores.status           IS '노출 상태 (PENDING(검수중) → APPROVED(노출) / REJECTED)';
COMMENT ON COLUMN stores.created_by       IS '등록자 FK (NULL = 시드 데이터)';
COMMENT ON COLUMN stores.rating_avg       IS '리뷰 평균 (denormalized, store_reviews 변동 시 동기화)';
COMMENT ON COLUMN stores.rating_count     IS '리뷰 개수 (denormalized)';
COMMENT ON COLUMN stores.created_at       IS '등록 시각';
COMMENT ON COLUMN stores.updated_at       IS '수정 시각';
COMMENT ON COLUMN stores.deleted_at       IS '삭제 시각 (soft delete)';



-- =============================================================================
-- T1 — 안정화 단계 테이블
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 2.1 volunteer_requests  (봉사자 역할 전환 요청 - 간소화)
-- -----------------------------------------------------------------------------
CREATE TABLE volunteer_requests (
    id            BIGSERIAL                  PRIMARY KEY,
    user_id       BIGINT                     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message       TEXT                       NOT NULL,
    status        volunteer_request_status   NOT NULL DEFAULT 'PENDING',
    processed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ                NOT NULL DEFAULT NOW()
);

-- 한 사용자가 동시에 PENDING 요청을 여러 개 보낼 수 없도록
CREATE UNIQUE INDEX uniq_volunteer_requests_one_pending
    ON volunteer_requests (user_id)
    WHERE status = 'PENDING';

CREATE INDEX idx_volunteer_requests_status_created
    ON volunteer_requests (status, created_at DESC);

COMMENT ON TABLE  volunteer_requests              IS 'USER → VOLUNTEER 역할 전환 요청 (관리자 승인 대상)';
COMMENT ON COLUMN volunteer_requests.id           IS '요청 ID';
COMMENT ON COLUMN volunteer_requests.user_id     IS '신청자 FK';
COMMENT ON COLUMN volunteer_requests.message      IS '신청자가 작성한 자유 텍스트 한 줄';
COMMENT ON COLUMN volunteer_requests.status       IS '처리 상태 (PENDING → APPROVED / REJECTED)';
COMMENT ON COLUMN volunteer_requests.processed_at IS '관리자 처리 시각';
COMMENT ON COLUMN volunteer_requests.created_at   IS '신청 시각';


-- -----------------------------------------------------------------------------
-- 2.2 chat_messages  (match_applications 에 직접 연결 — 신청자별 1:1 스레드)
-- -----------------------------------------------------------------------------
-- 매칭 1건당 N개의 1:1 채팅 스레드(작성자 ↔ 각 신청자)가 존재한다.
-- 작성자는 신청자와 채팅으로 대화한 뒤 채팅방 안에서 매칭 수락/거절 결정.
-- application 단위로 묶이므로 어떤 신청자의 스레드인지 명확하다.
-- -----------------------------------------------------------------------------
CREATE TABLE chat_messages (
    id              BIGSERIAL    PRIMARY KEY,
    application_id  BIGINT       NOT NULL REFERENCES match_applications(id) ON DELETE CASCADE,
    sender_id       BIGINT       REFERENCES users(id) ON DELETE SET NULL,
    content         TEXT         NOT NULL,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_application_created
    ON chat_messages (application_id, created_at DESC);

COMMENT ON TABLE  chat_messages                IS '채팅 메시지 (스레드 = match_applications 1건, 작성자 ↔ 한 신청자 1:1)';
COMMENT ON COLUMN chat_messages.id             IS '메시지 ID';
COMMENT ON COLUMN chat_messages.application_id IS '대화가 속한 신청 FK (참여자는 application.match.author_id + application.applicant_id 두 명)';
COMMENT ON COLUMN chat_messages.sender_id      IS '발신자 FK';
COMMENT ON COLUMN chat_messages.content        IS '메시지 내용';
COMMENT ON COLUMN chat_messages.read_at        IS '상대방이 읽은 시각';
COMMENT ON COLUMN chat_messages.created_at     IS '발송 시각';


-- -----------------------------------------------------------------------------
-- 2.3 match_reviews  (봉사 후기)
-- -----------------------------------------------------------------------------
CREATE TABLE match_reviews (
    id                BIGSERIAL    PRIMARY KEY,
    match_id          BIGINT       NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    reviewer_id       BIGINT       REFERENCES users(id) ON DELETE SET NULL,
    reviewee_id       BIGINT       REFERENCES users(id) ON DELETE SET NULL,
    rating            SMALLINT     NOT NULL CHECK (rating BETWEEN 1 AND 5),
    content           TEXT,
    proof_image_urls  TEXT[],
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, reviewer_id),
    CHECK (reviewer_id IS NULL OR reviewee_id IS NULL OR reviewer_id <> reviewee_id)
);

CREATE INDEX idx_match_reviews_reviewee
    ON match_reviews (reviewee_id, created_at DESC);

COMMENT ON TABLE  match_reviews                  IS '봉사 완료 후 양측이 서로 작성하는 후기 (통계의 원천 데이터)';
COMMENT ON COLUMN match_reviews.id               IS '후기 ID';
COMMENT ON COLUMN match_reviews.match_id         IS '대상 매칭 FK';
COMMENT ON COLUMN match_reviews.reviewer_id      IS '작성자 FK';
COMMENT ON COLUMN match_reviews.reviewee_id      IS '대상자 FK (작성자와 달라야 함)';
COMMENT ON COLUMN match_reviews.rating           IS '평점 (1~5)';
COMMENT ON COLUMN match_reviews.content          IS '후기 내용';
COMMENT ON COLUMN match_reviews.proof_image_urls IS '봉사 인증 사진 URL 배열';
COMMENT ON COLUMN match_reviews.created_at       IS '작성 시각';


-- -----------------------------------------------------------------------------
-- 2.4 store_reviews
-- -----------------------------------------------------------------------------
CREATE TABLE store_reviews (
    id              BIGSERIAL    PRIMARY KEY,
    store_id        BIGINT       NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    author_id       BIGINT       REFERENCES users(id) ON DELETE SET NULL,
    rating          SMALLINT     NOT NULL CHECK (rating BETWEEN 1 AND 5),
    is_pet_allowed  BOOLEAN      NOT NULL,
    content         TEXT         NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (store_id, author_id)
);

CREATE INDEX idx_store_reviews_store_created
    ON store_reviews (store_id, created_at DESC);

COMMENT ON TABLE  store_reviews                IS '매장 별점·리뷰 (반려동물 출입 가능 여부도 사용자 확인 형태로 수집)';
COMMENT ON COLUMN store_reviews.id             IS '리뷰 ID';
COMMENT ON COLUMN store_reviews.store_id       IS '대상 매장 FK';
COMMENT ON COLUMN store_reviews.author_id      IS '작성자 FK';
COMMENT ON COLUMN store_reviews.rating         IS '평점 (1~5)';
COMMENT ON COLUMN store_reviews.is_pet_allowed IS '방문 당시 반려동물 출입 가능 여부 (작성자가 체크박스로 입력)';
COMMENT ON COLUMN store_reviews.content        IS '리뷰 내용';
COMMENT ON COLUMN store_reviews.created_at     IS '작성 시각';
COMMENT ON COLUMN store_reviews.updated_at     IS '수정 시각';


-- -----------------------------------------------------------------------------
-- 2.5 reports  (신고 - 간소화: 신고자/대상자/사유만 기록)
-- -----------------------------------------------------------------------------
CREATE TABLE reports (
    id              BIGSERIAL    PRIMARY KEY,
    reporter_id     BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_user_id  BIGINT       REFERENCES users(id) ON DELETE SET NULL,
    reason          TEXT         NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (reporter_id, target_user_id)
);

CREATE INDEX idx_reports_target_created
    ON reports (target_user_id, created_at DESC);

COMMENT ON TABLE  reports                IS '사용자 신고 (관리자 검토용 단순 로그)';
COMMENT ON COLUMN reports.id             IS '신고 ID';
COMMENT ON COLUMN reports.reporter_id    IS '신고자 FK';
COMMENT ON COLUMN reports.target_user_id IS '신고 대상 사용자 FK';
COMMENT ON COLUMN reports.reason         IS '신고 사유 (자유 텍스트)';
COMMENT ON COLUMN reports.created_at     IS '신고 시각';


-- -----------------------------------------------------------------------------
-- 2.6 calendar_events  (정책 일정)
-- -----------------------------------------------------------------------------
CREATE TABLE calendar_events (
    id           BIGSERIAL     PRIMARY KEY,
    title        VARCHAR(200)  NOT NULL,
    description  TEXT,
    start_date   DATE          NOT NULL,
    end_date     DATE          NOT NULL,
    event_time   TIME,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CHECK (end_date >= start_date)
);

CREATE INDEX idx_calendar_events_dates
    ON calendar_events (start_date, end_date);

COMMENT ON TABLE  calendar_events             IS '시흥시 반려동물 정책 일정';
COMMENT ON COLUMN calendar_events.id          IS '일정 ID';
COMMENT ON COLUMN calendar_events.title       IS '일정 제목';
COMMENT ON COLUMN calendar_events.description IS '상세 설명';
COMMENT ON COLUMN calendar_events.start_date  IS '시작일';
COMMENT ON COLUMN calendar_events.end_date    IS '종료일 (>= start_date)';
COMMENT ON COLUMN calendar_events.event_time  IS '일정 시각 (선택)';
COMMENT ON COLUMN calendar_events.created_at  IS '레코드 생성 시각';
COMMENT ON COLUMN calendar_events.updated_at  IS '레코드 수정 시각';
