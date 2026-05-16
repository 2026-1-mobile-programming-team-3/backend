# API 명세서 — 좌표 → 행정구역 (`/geo`)

공통 사항(Base URL, 헤더, 에러 코드 등)은 `auth.md` 참고. 라우터 코드: `app/api/v1/geo.py` (prefix `/geo`, tag `Geo`).

---

## 1. 역지오코딩 — `GET /geo/reverse` [T1]

**인증 필요**

브라우저 Geolocation 또는 모바일 GPS 좌표를 카카오 Local API 로 reverse-geocode 한다. 홈 화면의 위치 pill, 매장 등록 시 자동 동 추출, 프로필 `region_si/region_dong` 갱신 등에 사용.

**Query Parameters**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| lat | float | Y | 위도 (-90 ~ 90) |
| lng | float | Y | 경도 (-180 ~ 180) |

**Response — 200 OK** (`ReverseGeocodeResponse`)

시흥시 내부:
```json
{
  "si": "시흥시",
  "sido": "경기도",
  "dong": "정왕동",
  "formatted_address": "경기도 시흥시 정왕동",
  "is_in_siheung": true,
  "label": "정왕동"
}
```

시흥시 외부:
```json
{
  "si": "강남구",
  "sido": "서울특별시",
  "dong": "역삼동",
  "formatted_address": "서울특별시 강남구 역삼동",
  "is_in_siheung": false,
  "label": "역삼동 (시흥시 외부)"
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| si | string \| null | `region_2depth_name` (예: 시흥시, 강남구) |
| sido | string \| null | `region_1depth_name` (예: 경기도) |
| dong | string \| null | `region_3depth_name` 또는 `region_4depth_name` |
| formatted_address | string | 전체 주소 |
| is_in_siheung | boolean | `sido == "경기도" AND si == "시흥시"` |
| label | string | 시흥시 내부면 동 이름만, 외부면 `"{dong} (시흥시 외부)"` |

- 행정동(`region_type=H`) 우선 선택, 없으면 법정동(`B`).
- 환경변수 `KAKAO_REST_API_KEY` 필수.

**Errors**

| 상태 코드 | 설명 |
| --- | --- |
| 400 | 좌표 범위 외 (lat ∉ [-90, 90] 또는 lng ∉ [-180, 180]) |
| 401 | 인증 실패 |
| 404 | 카카오 응답 `documents` 가 비어 있음 (해상·해외 등) |
| 502 | 카카오 API 호출 실패 또는 200 아닌 응답 |
