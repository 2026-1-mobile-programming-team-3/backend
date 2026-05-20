# API 명세서 — 반려동물 (`/users/me/pets`)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/pets.py` (prefix `/users/me/pets`, tag `pets`).

> 등록된 펫 목록은 `GET /users/me` 응답의 `pets` 필드(`users.md` §1.1)로 받는다. 본 문서는 펫 CRUD 3개 엔드포인트만 다룬다.

---

## 1. 반려동물 등록 — `POST /users/me/pets` [T0]

**인증 필요**

**Request Body** (`PetCreate`)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 반려동물 이름 (trim 후 빈 문자열 불가) |
| species | string | Y | `DOG` / `CAT` / `OTHER` |
| breed | string | N | 품종 |
| age | integer | N | 나이 (≥ 0) |
| weight_kg | float | N | 체중 (kg, > 0) |
| is_neutered | boolean | Y | 중성화 여부 |
| gender | string | N | `MALE` / `FEMALE` / `UNKNOWN` (기본 `UNKNOWN`) |
| photo_url | string | N | 사진 URL |
| note | string | N | 특이사항 (알레르기·복용 약·성격 등 자유 메모, 최대 500자) |

**Response — 201 Created** (`PetResponse`)
```json
{
  "id": 1,
  "name": "초코",
  "species": "DOG",
  "breed": "말티즈",
  "age": 3,
  "weight_kg": 4.2,
  "is_neutered": false,
  "gender": "MALE",
  "photo_url": "https://storage.example.com/pets/choco.jpg",
  "note": "닭고기 알레르기 있음. 산책 시 줄 강하게 당기는 편.",
  "created_at": "2026-04-15T12:00:00Z",
  "updated_at": "2026-04-15T12:00:00Z"
}
```

**Errors**: 400(유효성 검증) / 401.

---

## 2. 반려동물 수정 — `PATCH /users/me/pets/{pet_id}` [T1]

**인증 필요** / **Path**: `pet_id` (integer)

**Request Body** (`PetUpdate` — 변경할 필드만 전송, 모두 옵셔널)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| name | string | trim 후 빈 문자열 불가 |
| breed | string | |
| age | integer | ≥ 0 |
| weight_kg | float | > 0 |
| is_neutered | boolean | |
| gender | string | `MALE` / `FEMALE` / `UNKNOWN` |
| photo_url | string | |
| note | string | 특이사항 (최대 500자, `null` 로 비울 수 있음) |

> `species`는 등록 시 결정되며 수정 불가.

**Response — 200 OK** — `PetResponse` (1과 동일 스키마).

**Errors**: 400 / 401 / 403(본인의 반려동물 아님) / 404.

---

## 3. 반려동물 삭제 — `DELETE /users/me/pets/{pet_id}` [T1]

**인증 필요** / **Path**: `pet_id` (integer)

**Response — 204 No Content** (응답 본문 없음)

**Errors**: 401 / 403(본인의 반려동물 아님) / 404.

---

## 부록. 스키마

| Enum | 값 |
| --- | --- |
| `PetSpecies` | `DOG`, `CAT`, `OTHER` |
| `PetGender` | `MALE`, `FEMALE`, `UNKNOWN` |

- DB 모델: `app/models/user.py:Pet` — `weight_kg`는 `NUMERIC(5,2)`, `age`는 `SMALLINT`, `note`는 `VARCHAR(500)`.
- CHECK 제약: `age IS NULL OR age >= 0`, `weight_kg IS NULL OR weight_kg > 0`.
- `note` 는 공백만 입력 시 서버에서 `null` 로 정규화. 길이 검증은 Pydantic(`PetCreate`/`PetUpdate`) 단계에서 수행.
