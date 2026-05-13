from pydantic import BaseModel


class ReverseGeocodeResponse(BaseModel):
    si: str | None         # region_2depth_name, 예: "시흥시"
    sido: str | None       # region_1depth_name, 예: "경기도"
    dong: str | None       # region_3depth_name (또는 4), 예: "정왕동"
    formatted_address: str # 전체 주소 ("경기도 시흥시 정왕동")
    is_in_siheung: bool    # 경기도 시흥시 여부
    label: str             # 표시용 라벨: 시흥시 내부면 "정왕동", 외부면 "역삼동 (시흥시 외부)"
