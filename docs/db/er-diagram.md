```mermaid
erDiagram
    users {
        bigint id PK "고유 ID"
        varchar email "로그인 이메일 (유일)"
        varchar nickname "닉네임 (유일)"
        user_role role "권한 (USER/VOLUNTEER/ADMIN)"
        timestamptz deleted_at "탈퇴 시각 (soft delete)"
    }
    devices {
        bigint id PK "디바이스 ID"
        bigint user_id FK "소유 사용자"
        text fcm_token "FCM 등록 토큰 (유일)"
    }
    refresh_tokens {
        bigint id PK "토큰 레코드 ID"
        bigint user_id FK "소유 사용자"
        bigint device_id FK "발급 디바이스 (선택)"
        varchar token_hash "SHA-256 해시 (원문 미저장)"
        timestamptz expires_at "만료 시각"
    }
    pets {
        bigint id PK "반려동물 ID"
        bigint user_id FK "보호자"
        varchar name "이름"
        pet_species species "종 (DOG/CAT/OTHER)"
        boolean is_neutered "중성화 여부"
    }
    notifications {
        bigint id PK "알림 ID"
        bigint user_id FK "수신자"
        notification_category category "분류"
        varchar title "제목"
        timestamptz read_at "읽은 시각 (NULL=안읽음)"
    }
    matches {
        bigint id PK "요청 글 ID"
        bigint author_id FK "작성자 (보호자)"
        bigint pet_id FK "대상 반려동물 (선택)"
        varchar title "제목"
        match_status status "진행 상태"
        date desired_date "희망 일정"
        timestamptz deleted_at "삭제 시각 (soft delete)"
    }
    match_applications {
        bigint id PK "신청 ID"
        bigint match_id FK "대상 매칭 글"
        bigint applicant_id FK "신청 봉사자"
        application_status status "신청 상태 (PENDING/ACCEPTED/REJECTED)"
    }
    chat_messages {
        bigint id PK "메시지 ID"
        bigint application_id FK "속한 신청 (1:1 스레드)"
        bigint sender_id FK "발신자 (선택)"
        text content "메시지 내용"
        timestamptz read_at "상대방 읽은 시각"
    }
    match_reviews {
        bigint id PK "후기 ID"
        bigint match_id FK "대상 매칭"
        bigint reviewer_id FK "작성자 (선택)"
        bigint reviewee_id FK "대상자 (선택)"
        smallint rating "평점 (1~5)"
    }
    stores {
        bigint id PK "매장 ID"
        bigint created_by FK "등록자 (NULL=시드)"
        varchar name "상호명"
        store_category category "분류 (CAFE/RESTAURANT/PARK)"
        store_status status "노출 상태"
        numeric rating_avg "리뷰 평균 (비정규화)"
    }
    store_reviews {
        bigint id PK "리뷰 ID"
        bigint store_id FK "대상 매장"
        bigint author_id FK "작성자 (선택)"
        smallint rating "평점 (1~5)"
        boolean is_pet_allowed "반려동물 출입 가능 여부"
    }
    volunteer_requests {
        bigint id PK "요청 ID"
        bigint user_id FK "신청자"
        volunteer_request_status status "처리 상태 (PENDING/APPROVED/REJECTED)"
    }
    reports {
        bigint id PK "신고 ID"
        bigint reporter_id FK "신고자"
        bigint target_user_id FK "신고 대상 (선택)"
        text reason "신고 사유"
    }
    calendar_events {
        bigint id PK "일정 ID"
        varchar title "제목"
        date start_date "시작일"
        date end_date "종료일"
    }

    %% Auth 도메인
    users ||--o{ devices : "디바이스 소유"
    users ||--o{ refresh_tokens : "토큰 발급"
    devices |o--o{ refresh_tokens : "디바이스 연결"
    users ||--o{ pets : "반려동물 등록"
    users ||--o{ volunteer_requests : "봉사자 역할 신청"

    %% Notification 도메인
    users ||--o{ notifications : "알림 수신"

    %% Match 도메인
    users ||--o{ matches : "요청 글 작성"
    pets |o--o{ matches : "이동 지원 대상"
    matches ||--o{ match_applications : "봉사 신청 접수"
    users ||--o{ match_applications : "봉사 신청"
    match_applications ||--o{ chat_messages : "1:1 채팅 스레드"
    users |o--o{ chat_messages : "메시지 발신"
    matches ||--o{ match_reviews : "봉사 후기 대상"
    users |o--o{ match_reviews : "후기 작성"
    users |o--o{ match_reviews : "후기 수신"

    %% Map 도메인
    users |o--o{ stores : "매장 등록"
    stores ||--o{ store_reviews : "매장 리뷰"
    users |o--o{ store_reviews : "리뷰 작성"

    %% Report 도메인
    users ||--o{ reports : "신고 접수"
    users |o--o{ reports : "신고 대상"
```
