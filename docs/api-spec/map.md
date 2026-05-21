# API 명세서 — 지도/장소 서비스 (Map)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/maps.py` (prefix `/maps`, tag `Maps`).

> 좌표 → 행정구역 변환(`GET /geo/reverse`)은 별도 라우터 — `geo.md` 참고.
> 매장 즐겨찾기는 `favorites.md` 참고.

---

## 5.0 공통 — 입력 제약·차단 가시성

- **좌표(`latitude`/`longitude`, `lat`/`lng`)**: 모든 지도 엔드포인트에서 NaN/Inf 거부, 범위(±90/±180) 강제. PUT은 둘 다 함께 보내지 않으면 422.
- **검색 키워드 길이**: `GET /maps/stores/search?keyword=`는 **1~100자**만 허용. 초과 시 422 (ILIKE 기반 검색이라 거대 문자열 차단).
- **리뷰 본문**: `POST /maps/stores/{id}/reviews`의 `content` 길이는 **1~2,000자**.
- **차단 가시성**: `/maps/volunteers`(봉사자 위치)는 §3.0과 동일한 양방향 차단 필터를 적용. 일반 매장 검색/조회는 매장 데이터에 작성자 개념이 약하므로 별도 차단 적용 없음 — 단, 매장 리뷰는 작성자가 표기되므로 향후 인증 컨텍스트에서 확장 가능 (현재는 비인증 GET이므로 미적용).

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
      "thumbnail_url": "https://storage.example.com/stores/101.jpg",
      "rating_avg": 4.5,
      "is_favorited": false,
      "distance_m": 320.5
    }
  ]
}
```

> `distance_m`: 요청 좌표에서 매장까지의 거리(미터, 소수점 1자리). `status=APPROVED`이고 미삭제 매장만 노출.
> `thumbnail_url`: 매장 대표 사진(`photo_urls` 배열 첫 번째). 없으면 `null`.
> `rating_avg`: 매장 리뷰 평점 평균(소수점 1자리). 리뷰 0건이면 `null`.
> `is_favorited`: 인증된 요청에 한해 본인 즐겨찾기 여부. 비인증 호출 시 항상 `false`.

> **언제 5.1 vs 5.1B(viewport) 를 쓰나?**
> - **5.1 (`GET /maps/stores`)** — "내 주변" 카드/리스트 UI 처럼 **사용자 위치 기준 반경 검색 + 거리 표시**가 필요한 경우.
> - **5.1B (`GET /maps/stores/viewport`)** — 지도 화면 마커 렌더처럼 **카메라 viewport 안의 매장만 박스로 잘라오는** 경우. 거리 정보 없음, 카테고리 필터 옵션 있음.

---

### 5.1B 지도 viewport 매장 조회 — `GET /maps/stores/viewport` [T0]

**인증 불필요**

지도 카메라의 4 모서리(`sw`=남서, `ne`=북동) 좌표를 받아 PostGIS `ST_MakeEnvelope` 박스 안의 `APPROVED` 매장을 반환한다. 5.1과 달리 **거리 정보·정렬 없음** — 마커 렌더 전용이라 클라이언트가 줌 레벨에 따라 호출 여부를 결정하고, 결과를 그대로 마커로 찍는다.

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| sw_lat | float | Y | bbox 남서 위도 (-90 ~ 90) |
| sw_lng | float | Y | bbox 남서 경도 (-180 ~ 180) |
| ne_lat | float | Y | bbox 북동 위도 (-90 ~ 90) |
| ne_lng | float | Y | bbox 북동 경도 (-180 ~ 180) |
| category | string | N | `CAFE` / `RESTAURANT` / `PARK` / `PET_HOTEL` — 카테고리 필터 |

제약: `sw_lat < ne_lat` 그리고 `sw_lng < ne_lng` 이어야 함 (위반 시 422). 날짜변경선을 가로지르는 박스(국내 서비스이므로 미지원).

**Response — 200 OK**

```json
{
  "stores": [
    {
      "store_id": 36,
      "name": "정왕본동 도그파크",
      "latitude": 37.3493,
      "longitude": 126.7459,
      "category": "PARK",
      "is_pet_allowed": true,
      "rating_avg": 4.2,
      "rating_count": 8
    }
  ],
  "truncated": false
}
```

> `rating_avg`: 리뷰 0건이면 `null`. `rating_count` 와 함께 클라이언트가 별점 표시 여부 결정.
> `truncated`: 결과가 **200건 상한**에 잘려서 일부만 반환된 경우 `true`. 클라이언트는 "더 확대해 주세요" 같은 힌트를 띄울 수 있다.
> **bbox 응답 정렬은 `id` 오름차순** (안정적 페이지네이션이나 캐시 키 비교 용도). 거리·인기순 정렬은 5.1 사용.

**Errors**: 422 (좌표 페어 검증 실패).

**클라이언트 가이드 (Android — NaverMap 기준)**

1. **줌 임계값 게이팅** — `naverMap.cameraPosition.zoom < 11` 이면 API 호출 자체를 생략 (시 전체 보기 줌에서 마커 무의미). 임계 이상에서만 호출.
2. **bbox 추출** — `naverMap.contentBounds` 에서 `southWest`/`northEast` `LatLng` 를 그대로 `sw_lat/sw_lng/ne_lat/ne_lng` 로 매핑.
3. **camera idle 시 호출** — `OnCameraIdleListener` 에 디바운스(예: 300ms) 걸고 호출. 카메라 이동 중에는 호출하지 말 것.
4. **클러스터링** — 줌 11~13 구간은 NaverMap `MarkerClustering` (구 `Clusterer`) 으로 묶고, 14 이상에서 개별 마커. 백엔드는 항상 raw points 반환.
5. **truncated=true 처리** — "더 확대해 주세요" Snackbar 노출 권장. 임계 초과 박스에서 매장이 200개 넘는 케이스 (현재 시흥시 60건이라 당분간 발생 안 함, 매장 증가에 대비).
6. **5.1 (radius) 와의 분담** — "내 주변" 탭/카드형 리스트(거리 표시 필요)는 5.1, 지도 화면 마커는 5.1B.

---

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | `lat`/`lng` 누락, `lat` 범위 초과(±90), `lng` 범위 초과(±180), 또는 `radius` 범위 외(1 미만/50000 초과) |

---

### 5.2 주변 봉사 위치 표시 — `GET /maps/volunteers` [T0]

**인증 필요 (봉사자 권한 — `VOLUNTEER` 또는 `ADMIN`)**

`matches.status = 'WAITING'`이고 미삭제인 매칭 요청만 노출 (이미 진행/완료된 건 제외). 결과 200건 cap, `created_at DESC` 정렬.

> **차단 가시성**: 본인이 차단했거나 본인을 차단한 작성자의 봉사 요청은 결과에서 제외된다 (§5.0).

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
  "category": "CAFE",
  "rating_avg": 4.5,
  "review_pet_allowed_rate": 0.92,
  "is_favorited": false,
  "plans": []
}
```

> `is_favorited`: 인증된 요청에 한해 본인 즐겨찾기 여부. 비인증 호출 시 항상 `false`.
> `plans`: `category=PET_HOTEL` 인 매장에서만 채워짐. 그 외 카테고리는 항상 빈 배열. 각 항목은 `{plan_name, price_krw, display_order}`. 자세한 비교/요약 API 는 `§5.12 GET /maps/pet-hotels` 참고.

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
| keyword | string | Y | 상호명 또는 주소 키워드 (1~100자, ILIKE 기반) |

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
| category | string | N | `CAFE` / `RESTAURANT` / `PARK` / `PET_HOTEL` (코드 기준 enum) |
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

### 5.6 ~ 5.8 — **폐기됨 (Deprecated, 410 Gone)**

| 메서드 | 경로 | 상태 |
| --- | --- | --- |
| POST | `/maps/stores` | 410 Gone |
| PUT | `/maps/stores/{store_id}` | 410 Gone |
| DELETE | `/maps/stores/{store_id}` | 410 Gone |

응답 본문 예:
```json
{ "detail": "이 엔드포인트는 폐기되었습니다. POST /maps/store-requests 로 추가/수정 요청을 제출하세요." }
```

> 사용자 셀프 등록·수정·삭제는 모두 **점주 인증 기반 요청 워크플로우** (`§5.13 /maps/store-requests`) 로 일원화됐다.
> 관리자 직접 수정/삭제는 SQLAdmin UI 사용. 검수는 `/admin/store-requests` (admin.md §2 참고).

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
| content | string | Y | 리뷰 내용 (1~2,000자) |

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

---

### 5.12 펫호텔 가격 비교 — `GET /maps/pet-hotels` [T1]

**인증 불필요**

기준 좌표 주변(`radius` 반경, 기본 5km)의 `category=PET_HOTEL` 매장과 각 매장의 가격 플랜, 가격 요약을 한 번에 반환한다. 가격 비교 화면(1:N) 및 1:1 비교(클라이언트가 두 매장 id 로 매장 상세 두 번 호출하거나, 본 API 결과에서 두 카드 추출) 용도.

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| lat | float | Y | - | 위도 (-90 ~ 90, 유한값) |
| lng | float | Y | - | 경도 (-180 ~ 180, 유한값) |
| radius | integer | N | 5000 | 검색 반경 (m), 1 ~ 50,000 |

**Response — 200 OK** (`PetHotelListResponse`)

거리 오름차순, 50건 cap.

```json
{
  "pet_hotels": [
    {
      "store_id": 207,
      "name": "배곧 펫호텔",
      "address": "경기도 시흥시 배곧동 ...",
      "latitude": 37.3752,
      "longitude": 126.7281,
      "distance_m": 320.5,
      "is_pet_allowed": true,
      "thumbnail_url": "https://storage.example.com/stores/207.jpg",
      "rating_avg": 4.6,
      "rating_count": 12,
      "plan_count": 3,
      "min_price_krw": 40000,
      "max_price_krw": 75000,
      "plans": [
        {"plan_name": "1박 소형견", "price_krw": 40000, "display_order": 0},
        {"plan_name": "1박 중형견", "price_krw": 55000, "display_order": 1},
        {"plan_name": "1박 대형견", "price_krw": 75000, "display_order": 2}
      ]
    }
  ]
}
```

> `min_price_krw`/`max_price_krw`: plans 가 비어 있으면 `null`. 클라이언트는 "가격 정보 미등록" 으로 표시.
> `rating_avg`: 리뷰 0건이면 `null`.
> `distance_m`: 미터 단위, 소수점 1자리.

**클라이언트 활용 가이드**

- **1:N 카드 비교**: 본 API 결과를 그대로 카드 리스트로. 정렬 옵션(거리/최저가/평점)은 클라이언트 측에서 메모리 정렬.
- **1:1 상세 비교**: 두 매장 id 를 가지고 `GET /maps/stores/{id}` 를 두 번 호출 → 각 응답의 `plans` 필드로 표 그리기.
- **지도 시각화**: 각 항목의 (lat, lng, min_price_krw) 를 지도 마커 + 가격 라벨로 렌더 가능.

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 422 | lat/lng/radius 범위 또는 유한성 검사 실패 |

---

### 5.13 매장 추가/수정 요청 (`/maps/store-requests`) [T1]

기존 `POST /maps/stores`(5.6) 를 대체하는 **점주 인증 기반 요청 워크플로우**.
사용자가 자신이 운영하는 매장임을 증빙하는 자료(`proof_urls`)와 함께 추가(`ADD`) 또는 수정(`UPDATE`) 요청을 제출하고, 관리자(`/admin/store-requests` — admin.md §2)가 검수한다.

> **증빙 파일 처리**: 백엔드는 파일 자체를 받지 않는다. 클라이언트가 외부 비공개 스토리지(예: Firebase Storage 비공개 버킷, 카카오 클라우드 OBS)에 업로드해 얻은 URL 문자열만 `proof_urls` 배열로 전송. 일반 매장 사진(`photo_urls`)과 같은 패턴.

#### 5.13.1 요청 제출 — `POST /maps/store-requests`

**인증 필요** / **Rate limit**: 5/hour

**Request Body** (`StoreRequestCreate`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| type | string | Y | `ADD` 또는 `UPDATE` |
| target_store_id | integer | (UPDATE 시 Y) | UPDATE 대상 매장 id. ADD 일 때는 보내지 말 것 |
| payload | object | Y | 매장 정보 + (PET_HOTEL 인 경우) `plans` 배열 — 아래 §payload 참고 |
| proof_urls | string[] | N | 사업자등록증 등 증빙 자료 URL 배열 (최대 10개) |
| message | string | N | 관리자에게 남기는 메모 (최대 1000자) |

##### payload 스키마

| 필드 | 타입 | ADD 필수 | UPDATE 필수 | 설명 |
| --- | --- | --- | --- | --- |
| name | string | Y | N | 매장 이름 (1~100자) |
| address | string | Y | N | 매장 주소 (1~255자) |
| category | string | Y | N | `CAFE` / `RESTAURANT` / `PARK` / `PET_HOTEL` |
| is_pet_allowed | boolean | Y | N | 반려동물 출입 가능 여부 |
| latitude | float | Y | N | 위도 (-90 ~ 90, 유한값). lng 와 페어로 보내야 함 |
| longitude | float | Y | N | 경도 (-180 ~ 180, 유한값). lat 와 페어로 보내야 함 |
| phone | string | N | N | 전화번호 (최대 20자) |
| operating_hours | string | N | N | 영업시간 (최대 100자) |
| photo_urls | string[] | N | N | 매장 사진 URL 배열 |
| plans | object[] | N | N | **PET_HOTEL 매장 전용**. 각 항목 `{plan_name(1~100), price_krw(>=0), display_order?}`. plan_name 중복 금지. 전체 교체 시맨틱 — UPDATE 승인 시 기존 plans 전부 삭제 후 새로 INSERT. |

**예시 — PET_HOTEL ADD**
```json
{
  "type": "ADD",
  "payload": {
    "name": "배곧 펫호텔",
    "address": "경기도 시흥시 배곧동 ...",
    "category": "PET_HOTEL",
    "is_pet_allowed": true,
    "latitude": 37.3752,
    "longitude": 126.7281,
    "phone": "031-000-0000",
    "operating_hours": "00:00-24:00",
    "photo_urls": ["https://..."],
    "plans": [
      {"plan_name": "1박 소형견", "price_krw": 40000},
      {"plan_name": "1박 중형견", "price_krw": 55000}
    ]
  },
  "proof_urls": ["https://private-bucket/.../biz-license.pdf"],
  "message": "본인이 운영하는 매장입니다."
}
```

**예시 — UPDATE (가격만 변경)**
```json
{
  "type": "UPDATE",
  "target_store_id": 207,
  "payload": {
    "plans": [
      {"plan_name": "1박 소형견", "price_krw": 45000},
      {"plan_name": "1박 중형견", "price_krw": 60000}
    ]
  }
}
```

**Response — 201 Created** (`StoreRequestCreatedResponse`)
```json
{
  "request_id": 7,
  "type": "ADD",
  "target_store_id": null,
  "status": "PENDING",
  "created_at": "2026-05-21T09:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | UPDATE 시 본인이 점주(`owner_user_id`)로 인증된 매장이 아님 |
| 404 | UPDATE 시 대상 매장 없음 / 미승인 / 삭제됨 |
| 409 | 동일 사용자의 ADD PENDING 1건이 이미 있음 (또는) 동일 매장의 UPDATE PENDING 이 이미 있음 |
| 422 | 유효성 검사 실패 (필드 누락/범위/`plans` 카테고리 불일치/`plan_name` 중복 등) |
| 429 | Rate limit 초과 (5/hour) |

> **점주 부여 시점**: ADD 요청이 승인되는 순간 신청자가 해당 매장의 `owner_user_id` 로 박힌다. 이후 본인이 같은 매장에 대해 UPDATE 요청을 다시 보낼 수 있음.
> **시드 매장 (`owner_user_id IS NULL`)**: 데이터베이스에 미리 들어 있는 시 운영 시드 매장은 점주 미배정 상태이므로 일반 UPDATE 요청 불가. 정보 변경은 SQLAdmin 으로 관리자가 직접.

---

#### 5.13.2 본인 요청 목록 — `GET /maps/store-requests`

**인증 필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| status | string | N | (전체) | `PENDING` / `APPROVED` / `REJECTED` |
| page | integer | N | 1 | |
| size | integer | N | 20 | 1~100 |

**Response — 200 OK** (`StoreRequestListResponse`) — `items[i]` 는 `StoreRequestItem`:

```json
{
  "items": [
    {
      "request_id": 7,
      "type": "ADD",
      "target_store_id": null,
      "payload": { "...매장 정보..." },
      "proof_urls": ["https://..."],
      "message": "본인이 운영하는 매장입니다.",
      "status": "REJECTED",
      "review_note": "사업자등록증 사본이 흐려서 식별 불가합니다. 재제출 부탁드립니다.",
      "processed_at": "2026-05-21T10:30:00Z",
      "created_at": "2026-05-21T09:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

> 반려된 경우 `review_note` 로 사유 확인 가능 → 클라이언트는 폼 재진입 시 기존 payload 프리필 + 사유 안내.

#### 5.13.3 본인 요청 상세 — `GET /maps/store-requests/{request_id}`

**인증 필요** / **Path**: `request_id` — 본인 요청만 조회 가능. 본인 아닌 요청은 404 (존재 노출 회피).

목록 응답의 단일 항목(`StoreRequestItem`) 동일 스키마.

**Errors**: 401 / 404.

#### 5.13.4 본인 요청 취소 — `DELETE /maps/store-requests/{request_id}`

**인증 필요** / **Path**: `request_id`

PENDING 상태인 본인 요청만 취소(행 DELETE). 이미 처리된 요청은 취소 불가.

**Response — 204 No Content** (응답 본문 없음)

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 404 | 본인 요청 중 해당 id 없음 |
| 409 | 이미 처리된 요청(`APPROVED`/`REJECTED`) — 취소 불가 |

---

### 5.14 좌표 → 행정구역 변환 — `geo.md` 로 이동

`GET /geo/reverse` 는 별도 `geo` 라우터로 분리되었다. 명세는 `geo.md` 참고.
