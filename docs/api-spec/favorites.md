# API 명세서 — 매장 즐겨찾기 (`/users/me/favorites/stores`)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/favorites.py` (prefix `/users/me/favorites`, tag `favorites`).

> 매장 데이터(상세·검색·생성 등)는 `map.md` 참고. 본 문서는 즐겨찾기 CRUD 3개 엔드포인트만 다룬다.

---

## 1. 즐겨찾기 등록 — `POST /users/me/favorites/stores` [T1]

**인증 필요**

**Request Body** (`FavoriteCreateRequest`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| store_id | integer | Y | 즐겨찾기에 추가할 매장 ID |

**Response — 201 Created** (`FavoriteCreatedResponse`)
```json
{
  "favorite_id": 1,
  "store_id": 101,
  "created_at": "2026-05-06T12:00:00Z"
}
```

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 401 | 인증 실패 |
| 404 | 매장 없음 또는 미승인(`PENDING`/`REJECTED`) 또는 soft-delete |
| 409 | 이미 즐겨찾기에 등록됨 |

> DB 제약: `UNIQUE(user_id, store_id)`.

---

## 2. 즐겨찾기 해제 — `DELETE /users/me/favorites/stores/{store_id}` [T1]

**인증 필요** / **Path**: `store_id`

**Response — 204 No Content** (응답 본문 없음)

**Errors**: 401 / 404(본인 즐겨찾기에 없음).

---

## 3. 즐겨찾기 목록 조회 — `GET /users/me/favorites/stores` [T1]

**인증 필요**

**Query Parameters**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | integer | N | 1 | |
| size | integer | N | 20 | 1~100 |

**Response — 200 OK** (`FavoriteListResponse`)
```json
{
  "items": [
    {
      "favorite_id": 1,
      "store_id": 101,
      "name": "배곧 댕댕카페",
      "category": "CAFE",
      "thumbnail_url": "https://storage.example.com/stores/101.jpg",
      "rating_avg": 4.5,
      "created_at": "2026-05-06T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

> `category` enum: `CAFE` / `RESTAURANT` / `PARK` (코드 기준 — 추가 카테고리는 enum 확장 후 노출). 매장이 soft-delete 됐거나 `PENDING`/`REJECTED` 로 전환된 항목은 자동 제외.
