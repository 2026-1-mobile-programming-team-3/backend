# API 명세서 — 지도/장소 서비스 (Map)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

---

## 5. 지도 / 장소 서비스 (Map)

### 5.1 반려동물 출입 가능 매장 지도 조회 — `GET /maps/stores` [T0]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| lat | float | Y | - | 위도 (-90 ~ 90) |
| lng | float | Y | - | 경도 (-180 ~ 180) |
| radius | integer | N | 2000 | 검색 반경 (m), 최대 50000 (50km) |

**Response — 200 OK**

PostGIS `ST_DWithin` 기반 반경 검색. 응답은 거리 오름차순 정렬, 최대 200건.

```json
{
  "stores": [
    {
      "store_id": 101,
      "name": "배곧 댕댕카페",
      "latitude": 37.3752,
      "longitude": 126.7281,
      "category": "CAFE",
      "is_pet_allowed": true,
      "distance_m": 320.5
    }
  ]
}
```

> `distance_m`: 요청 좌표에서 매장까지의 거리(미터, 소수점 1자리). `status=APPROVED`이고 미삭제 매장만 노출.

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | `lat`/`lng` 누락, `lat` 범위 초과(±90), `lng` 범위 초과(±180), 또는 `radius` 범위 외(1 미만/50000 초과) |

---

### 5.2 주변 봉사 위치 표시 — `GET /maps/volunteers` [T0]

**인증 필요 (봉사자 권한 — `VOLUNTEER` 또는 `ADMIN`)**

`matches.status = 'WAITING'`이고 미삭제인 매칭 요청만 노출 (이미 진행/완료된 건 제외). 결과 200건 cap, `created_at DESC` 정렬.

**Response — 200 OK**
```json
{
  "volunteer_requests": [
    {
      "request_id": 201,
      "title": "정왕동 실외견 병원 이동 부탁드립니다",
      "latitude": 37.3451,
      "longitude": 126.7322,
      "status": "WAITING"
    }
  ]
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 봉사자 권한 없음 (`USER` 토큰으로 호출) |

---

### 5.3 매장 상세 정보 조회 — `GET /maps/stores/{store_id}` [T0]

**인증 불필요** / **Path**: `store_id` (integer)

**Response — 200 OK**
```json
{
  "store_id": 101,
  "name": "배곧 댕댕카페",
  "address": "경기도 시흥시 서울대학로...",
  "phone": "031-123-4567",
  "operating_hours": "10:00 - 22:00",
  "photo_urls": ["url1.jpg", "url2.jpg"],
  "is_pet_allowed": true,
  "rating_avg": 4.5,
  "review_pet_allowed_rate": 0.92
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 404 | 존재하지 않는 매장 |

---

### 5.4 매장 검색 — `GET /maps/stores/search` [T1]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| keyword | string | Y | 상호명 또는 주소 키워드 |

**Response — 200 OK**
```json
{
  "results": [
    {
      "store_id": 101,
      "name": "배곧 댕댕카페",
      "address": "경기도 시흥시 서울대학로...",
      "category": "CAFE"
    }
  ]
}
```

---

### 5.5 지도 마커 필터링 — `GET /maps/stores/filter` [T1]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| category | string | N | `CAFE` / `RESTAURANT` / `PARK` |
| is_pet_allowed | boolean | N | 반려동물 출입 가능 여부 (공식 정보 기준) |

**Response — 200 OK**
```json
{
  "stores": [
    {
      "store_id": 101,
      "name": "배곧 댕댕카페",
      "latitude": 37.3752,
      "longitude": 126.7281,
      "category": "CAFE",
      "is_pet_allowed": true
    }
  ]
}
```

---

### 5.6 신규 매장 정보 등록 — `POST /maps/stores` [T1]

> 🚨 **임시 구현 — 카카오 지도 API로 변경 필요!**
> 현재는 클라이언트가 `latitude`/`longitude`를 직접 전송. 향후 카카오 지오코딩 API(`https://dapi.kakao.com/v2/local/search/address.json`)로 교체 필요. 환경변수 `KAKAO_REST_API_KEY` 추가 + `latitude`/`longitude` 필드 제거 + `address`만 입력받아 서버가 자동 좌표 변환하는 방식으로 전환 예정.

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 매장 이름 (1~100자) |
| address | string | Y | 매장 주소 (1~255자) |
| category | string | Y | `CAFE` / `RESTAURANT` / `PARK` |
| is_pet_allowed | boolean | Y | 반려동물 출입 가능 여부 |
| latitude | float | Y | ⚠️ 임시. 위도 (-90 ~ 90), 향후 자동 지오코딩으로 교체 |
| longitude | float | Y | ⚠️ 임시. 경도 (-180 ~ 180), 향후 자동 지오코딩으로 교체 |
| phone | string | N | 전화번호 (최대 20자) |
| operating_hours | string | N | 영업시간 (자유 포맷, 최대 100자) |
| photo_urls | string[] | N | 매장 사진 URL 배열 (기본 빈 배열) |

```json
{
  "name": "시흥 반려동물 공원",
  "address": "경기도 시흥시 정왕동 123",
  "category": "PARK",
  "is_pet_allowed": true,
  "latitude": 37.3451,
  "longitude": 126.7322,
  "phone": "031-000-0000",
  "operating_hours": "09:00-22:00",
  "photo_urls": []
}
```

**Response — 201 Created**
```json
{
  "store_id": 105,
  "status": "PENDING"
}
```

> 등록 직후 상태는 `PENDING`. 관리자 검수 후 `APPROVED`로 전환되어야 지도에 노출. `created_by`에는 현재 사용자 id가 자동 기록됨.

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검사 실패 (좌표 범위, 길이 제한 등) |
| 401 | 인증 실패 |

---

### 5.7 매장 정보 수정 — `PUT /maps/stores/{store_id}` [T2]

**인증 필요** (본인 등록 매장 또는 관리자) / **Path**: `store_id`

**Request Body**: 5.6과 동일 스키마지만 **모든 필드 옵션 (전송된 필드만 갱신, PATCH 시맨틱).** `latitude`/`longitude`는 **둘 다 함께 보내야** 함 — 한쪽만 보내면 400.

```json
{
  "is_pet_allowed": false,
  "operating_hours": "10:00-21:00"
}
```

**Response — 200 OK**
```json
{ "message": "성공적으로 처리되었습니다." }
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검사 실패, 또는 lat/lng 한쪽만 전송 |
| 401 | 인증 실패 |
| 403 | 본인이 등록한 매장이 아니고 관리자도 아님 |
| 404 | 매장 없음 (또는 이미 삭제됨) |

---

### 5.8 매장 삭제 — `DELETE /maps/stores/{store_id}` [T2]

**인증 필요** (본인 등록 매장 또는 관리자) / **Path**: `store_id`

Soft delete — `deleted_at = NOW()`로 표시. 이후 `GET /maps/stores/{id}` 등에서는 `404`로 응답.

**Response — 200 OK**
```json
{ "message": "성공적으로 처리되었습니다." }
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 본인이 등록한 매장이 아니고 관리자도 아님 |
| 404 | 매장 없음 (또는 이미 삭제됨) |

---

### 5.9 매장 리뷰 조회 — `GET /maps/stores/{store_id}/reviews` [T1]

**인증 불필요** / **Path**: `store_id`

**Response — 200 OK**
```json
{
  "reviews": [
    {
      "review_id": 50,
      "nickname": "댕댕이주인",
      "rating": 5,
      "is_pet_allowed": true,
      "content": "칸막이가 잘 되어 있어서 안심하고 밥 먹었어요!",
      "created_at": "2026-04-16T12:00:00Z"
    }
  ]
}
```

---

### 5.10 매장 리뷰 작성 — `POST /maps/stores/{store_id}/reviews` [T2]

**인증 필요** / **Path**: `store_id`

대상 매장은 `status='APPROVED'`이고 미삭제여야 함 (PENDING 매장은 리뷰 불가).

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| rating | integer | Y | 평점 (1~5) |
| is_pet_allowed | boolean | Y | 방문 당시 반려동물 출입 가능 여부 (체크박스) |
| content | string | Y | 리뷰 내용 (최소 1자) |

**Response — 201 Created**
```json
{
  "review_id": 51,
  "rating": 5,
  "is_pet_allowed": true,
  "content": "...",
  "created_at": "2026-04-16T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 유효성 검사 실패 (rating 범위, content 빈 문자열 등) |
| 401 | 인증 실패 |
| 404 | 매장 없음 또는 미승인 매장 |
| 409 | 동일 사용자가 동일 매장에 이미 리뷰 작성함 |

---

### 5.11 매장 리뷰 삭제 — `DELETE /maps/stores/{store_id}/reviews/{review_id}` [T2]

**인증 필요** (본인 작성만 — 관리자도 타인 리뷰 삭제 불가) / **Path**: `store_id`, `review_id`

**Response — 204 No Content** (응답 본문 없음)

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 본인이 작성한 리뷰가 아님 |
| 404 | `review_id` 없음 또는 path의 `store_id`와 불일치 |
