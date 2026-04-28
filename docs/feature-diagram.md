# 기능 다이어그램 — 시흥가개

본 문서는 시흥가개의 전체 기능 구조와 핵심 라이프사이클을 시각화한 것이다.
세부 명세는 `기능명세서.md`, `API명세서.md`, `db/DB설계.md` 참고.

GitHub·VS Code·Notion 등 대부분의 마크다운 뷰어에서 mermaid 다이어그램이 그대로 렌더링된다.

---

## 1. 전체 기능 마인드맵

6개 도메인과 46개 기능 전체. **★** = T0 (MVP 필수), 표시 없음 = T1, 점 (·) = T2.

```mermaid
mindmap
  root((시흥가개))
    사용자 관리 Auth
      회원가입 ★
      로그인 ★
      토큰 갱신 ★
      로그아웃 ★
      내 정보 조회 ★
      계정 정보 수정 ★
      비밀번호 변경
      계정 탈퇴
      반려동물 등록 ★
      반려동물 수정
      반려동물 삭제
      봉사자 역할 전환 요청
      관리자 봉사자 요청 목록
      관리자 봉사자 요청 승인 거부
    알림 Notification
      알림 목록 조회 ★
      알림 전체 읽음 처리
      읽지 않은 알림 개수 ★
      FCM 디바이스 토큰 등록 ★
    매칭 Match
      이동지원 요청 작성 ★
      이동지원 요청 수정 삭제
      이동지원 요청 목록 ★
      특정 요청 상세 ★
      봉사 신청하기 ★
      신청자 목록 작성자용 ★
      봉사자 매칭 수락 거절 ★
      매칭 상태 실시간 업데이트
      1대1 채팅
      봉사 완료 인증 후기
      ·개인 봉사 통계
    신고 차단 Report
      게시글 후기 신고
      채팅 내 유저 신고
      ·사용자 차단 등록
      ·차단 목록 조회 해제
    지도 장소 Map
      매장 지도 조회 ★
      주변 봉사 위치 ★
      매장 상세 정보 ★
      매장 검색
      마커 필터링
      신규 매장 등록
      ·매장 정보 수정 삭제
      매장 리뷰 조회
      ·매장 리뷰 작성 삭제
    뉴스 캘린더 News
      정책 뉴스 목록 ★
      정책 뉴스 상세
      월별 정책 캘린더
      ·특정일 정책 상세
```

---

## 2. 사용자 역할과 권한

3가지 역할(`USER` / `VOLUNTEER` / `ADMIN`)의 진입 경로와 접근 가능한 핵심 기능.

```mermaid
flowchart LR
    Guest([비회원]) -->|회원가입| User
    User[👤 USER<br>일반 사용자]
    Volunteer[🛠 VOLUNTEER<br>봉사자]
    Admin[🛡 ADMIN<br>관리자]

    User -->|봉사자 역할 전환 요청| Pending{{PENDING}}
    Pending -->|관리자 승인| Volunteer
    Pending -->|관리자 거부| User

    User -.->|접근 가능| UF[매장 지도<br>매장 리뷰<br>이동지원 요청 작성<br>마이페이지]
    Volunteer -.->|추가 접근| VF[봉사 위치 지도<br>봉사 신청<br>1:1 채팅<br>봉사 후기]
    Admin -.->|관리 권한| AF[봉사자 요청 승인<br>매장 등록 검수<br>신고 처리]

    classDef role fill:#243B6B,stroke:#1B3A8C,color:#fff
    classDef perm fill:#E1E8DA,stroke:#5C7C4D,color:#2F4326
    classDef state fill:#FFF1E5,stroke:#E8732E,color:#8C3A0A
    class User,Volunteer,Admin role
    class UF,VF,AF perm
    class Pending state
```

---

## 3. 매칭 라이프사이클 (State Diagram)

`matches.status` ENUM (`WAITING` / `MATCHING` / `PROGRESS` / `DONE`) 의 상태 전이.
매칭은 작성자(USER) ↔ 봉사자(VOLUNTEER) 양측의 액션으로 진행되며, **채팅은 신청 발생 직후부터** 작성자 ↔ 신청자 1:1로 가능하다 (수락 전 단계 포함).

```mermaid
stateDiagram-v2
    [*] --> WAITING : 작성자가 이동지원 요청 글 작성
    WAITING --> MATCHING : 봉사자가 신청 등록<br>(match_applications.status = PENDING)<br>→ 작성자가 채팅 시작 가능
    MATCHING --> WAITING : 모든 신청자가 거절 또는 자발 취소
    MATCHING --> PROGRESS : 작성자가 채팅 후 신청자 1명 수락<br>(application.status = ACCEPTED)<br>나머지 application = REJECTED 자동 처리
    PROGRESS --> DONE : 봉사 완료 인증 + 후기 작성
    DONE --> [*]

    note left of WAITING
        모집 중 — 봉사자에게 노출
        지도 마커 + 목록 노출
    end note
    note right of MATCHING
        신청자별 1:1 채팅 스레드 활성화
        chat_messages.application_id로 묶임
        (매칭 1건당 N개 스레드)
    end note
    note right of PROGRESS
        수락된 application의 스레드만 활성
        나머지는 비활성화 (메시지는 보존)
    end note
```

---

## 4. 봉사자 매칭 시나리오 (User Journey)

"이동 지원 요청 → 채팅 → 봉사 매칭 → 완료" 시나리오 한 사이클.

```mermaid
journey
    title 봉사자 매칭 한 사이클
    section 작성자 (USER)
      이동지원 요청 작성: 5: USER
      신청자 카드 확인: 4: USER
      신청자와 1:1 채팅: 4: USER
      대화 후 매칭 결정: 5: USER
      봉사 완료 인증: 5: USER
      봉사자에게 후기 작성: 4: USER
    section 봉사자 (VOLUNTEER)
      지도에서 요청 발견: 5: VOLUNTEER
      봉사 신청 등록: 4: VOLUNTEER
      작성자와 채팅 (자기소개·일정): 5: VOLUNTEER
      매칭 수락 알림 수신: 5: VOLUNTEER
      봉사 수행: 5: VOLUNTEER
      작성자에게 후기 작성: 4: VOLUNTEER
```

---

## 5. 데이터 모델 ERD (요약본)

15개 테이블 중 핵심 관계만. 자세한 컬럼은 `db/db-design.md` 참고.

```mermaid
erDiagram
    users ||--o{ pets : "보호자"
    users ||--o{ devices : "FCM"
    devices ||--o{ refresh_tokens : "발급"
    users ||--o{ notifications : "수신"
    users ||--o{ volunteer_requests : "역할 전환"
    users ||--o{ matches : "작성"
    users ||--o{ match_applications : "신청"
    users ||--o{ stores : "등록"
    users ||--o{ store_reviews : "리뷰"
    users ||--o{ chat_messages : "발신"
    users ||--o{ match_reviews : "후기"
    users ||--o{ reports : "신고"

    matches ||--o{ match_applications : "신청 받음"
    match_applications ||--o{ chat_messages : "1:1 스레드"
    matches ||--o{ match_reviews : "양방향 후기"
    pets ||--o{ matches : "대상 반려동물"

    stores ||--o{ store_reviews : "리뷰 받음"

    users {
        bigserial id PK
        varchar email UK
        varchar nickname UK
        user_role role
        timestamptz deleted_at
    }
    matches {
        bigserial id PK
        bigint author_id FK
        bigint pet_id FK
        geography location
        match_status status
        timestamptz deleted_at
    }
    match_applications {
        bigserial id PK
        bigint match_id FK
        bigint applicant_id FK
        application_status status
    }
    stores {
        bigserial id PK
        varchar name
        store_category category
        geography location
        text_array photo_urls
        store_status status
        numeric rating_avg
    }
    chat_messages {
        bigserial id PK
        bigint application_id FK
        bigint sender_id FK
        text content
        timestamptz read_at
    }
```

---

## 6. 우선순위 분포 (참고)

| 우선순위 | 정의 | 개수 |
| --- | --- | --- |
| **T0** | MVP 필수 — 1차 시연 전까지 반드시 구현 | 18 |
| **T1** | 부가 기능 — 안정화 단계에서 구현 | 19 |
| **T2** | 확장 기능 — 시간 여유 시 구현 | 8 |
| 합계 | | **45** |

> 기능명세서 표 기준. "매장 정보 수정 및 삭제" 한 줄을 분리해 46개 행으로 보는 시각도 있으나, 우선순위 카운트는 원본 CSV의 45개 기준.
