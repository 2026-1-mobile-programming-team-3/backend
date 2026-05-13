"""좌표 → 행정구역 reverse-geocoding (Kakao Local API)."""
from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.geo import ReverseGeocodeResponse

KAKAO_REVERSE_URL = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
SIHEUNG_SIDO = "경기도"
SIHEUNG_SI = "시흥시"


async def reverse_geocode(lat: float, lng: float) -> ReverseGeocodeResponse:
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="좌표 범위 오류")
    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}
    params = {"x": lng, "y": lat}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(KAKAO_REVERSE_URL, headers=headers, params=params)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"카카오 지도 API 호출 실패: {e}") from e
    if r.status_code != 200:
        # 카카오 에러 본문(errorType, message)을 그대로 전달해 디버깅을 쉽게.
        try:
            err_body = r.json()
            kakao_msg = err_body.get("message") or err_body.get("msg") or ""
            kakao_type = err_body.get("errorType") or ""
            parts = [f"카카오 {r.status_code}"]
            if kakao_type:
                parts.append(kakao_type)
            if kakao_msg:
                parts.append(kakao_msg)
            detail = " — ".join(parts)
        except Exception:
            detail = f"카카오 응답 오류: {r.status_code}"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    data = r.json()
    docs = data.get("documents") or []
    if not docs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 좌표의 행정구역을 찾을 수 없습니다.")

    # 행정동(H) 우선, 없으면 법정동(B)
    doc = next((d for d in docs if d.get("region_type") == "H"), None) or docs[0]
    sido = doc.get("region_1depth_name") or None
    si = doc.get("region_2depth_name") or None
    dong = doc.get("region_3depth_name") or None
    address = doc.get("address_name") or ""

    is_in_siheung = sido == SIHEUNG_SIDO and si == SIHEUNG_SI
    if is_in_siheung:
        label = dong or "(알 수 없음)"
    else:
        label = f"{dong or si or '위치 미상'} (시흥시 외부)"

    return ReverseGeocodeResponse(
        si=si, sido=sido, dong=dong,
        formatted_address=address,
        is_in_siheung=is_in_siheung,
        label=label,
    )
