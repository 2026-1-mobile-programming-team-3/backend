# API 명세서 — 지도/장소 서비스 (Map)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고.

---

## 5. 지도 / 장소 서비스 (Map)

### 5.1 반려동물 출입 가능 매장 지도 조회 — `GET /maps/stores` [T0]

**인증 불필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| lat | float | Y | - | 위도 |
| lng | float | Y | - | 경도 |
| radius | integer | N | 2000 | 검색 반경 (m) |

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

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 좌표 누락 또는 잘못된 형식 |

---

### 5.2 주변 봉사 위치 표시 — `GET /maps/volunteers` [T0]

**인증 필요 (봉사자 권한)**

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
| 403 | 봉사자 권한 없음 |

---

### 5.3 매장 상세 정보 조회 — `GET /maps/stores/{storeId}` [T0]

**인증 불필요** / **Path**: `storeId` (integer)

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

**인증 필요**

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 매장 이름 |
| address | string | Y | 매장 주소 |
| category | string | Y | 카테고리 |
| is_pet_allowed | boolean | Y | 반려동물 출입 가능 여부 |

**Response — 201 Created**
```json
{
  "store_id": 105,
  "status": "PENDING"
}
```

> 등록 직후 상태는 `PENDING`. 관리자 검수 후 `APPROVED`로 전환되어야 지도에 노출.

---

### 5.7 매장 정보 수정 — `PUT /maps/stores/{storeId}` [T2]

**인증 필요** (본인 등록 매장 또는 관리자) / **Path**: `storeId`

**Request Body**: 수정할 필드 (5.6과 동일 스키마)

**Response — 200 OK**
```json
{ "message": "성공적으로 처리되었습니다." }
```

---

### 5.8 매장 삭제 — `DELETE /maps/stores/{storeId}` [T2]

**인증 필요** (본인 등록 매장 또는 관리자) / **Path**: `storeId`

**Response — 200 OK**
```json
{ "message": "성공적으로 처리되었습니다." }
```

---

### 5.9 매장 리뷰 조회 — `GET /maps/stores/{storeId}/reviews` [T1]

**인증 불필요** / **Path**: `storeId`

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

### 5.10 매장 리뷰 작성 — `POST /maps/stores/{storeId}/reviews` [T2]

**인증 필요** / **Path**: `storeId`

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| rating | integer | Y | 평점 (1~5) |
| is_pet_allowed | boolean | Y | 방문 당시 반려동물 출입 가능 여부 (체크박스) |
| content | string | Y | 리뷰 내용 |

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
| 409 | 동일 사용자가 동일 매장에 이미 리뷰 작성함 |

---

### 5.11 매장 리뷰 삭제 — `DELETE /maps/stores/{storeId}/reviews/{reviewId}` [T2]

**인증 필요** (본인 작성만) / **Path**: `storeId`, `reviewId`

**Response — 204 No Content**
