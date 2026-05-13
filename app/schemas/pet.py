from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.enums import PetGender, PetSpecies


class PetCreate(BaseModel):
    name: str
    species: PetSpecies
    breed: Optional[str] = None
    age: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    is_neutered: bool
    gender: PetGender = PetGender.UNKNOWN
    photo_url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("이름을 입력해주세요.")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("나이는 0 이상이어야 합니다.")
        return v

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("체중은 0보다 커야 합니다.")
        return v


class PetUpdate(BaseModel):
    # 마이페이지에서 이름·품종·나이·성별·중성화 여부·체중·사진을 모두 편집할 수 있어야 한다.
    name: Optional[str] = None
    breed: Optional[str] = None
    age: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    is_neutered: Optional[bool] = None
    gender: Optional[PetGender] = None
    photo_url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("이름을 입력해주세요.")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("나이는 0 이상이어야 합니다.")
        return v

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("체중은 0보다 커야 합니다.")
        return v


class PetResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    species: PetSpecies
    breed: Optional[str]
    age: Optional[int]
    weight_kg: Optional[Decimal]
    is_neutered: bool
    gender: PetGender
    photo_url: Optional[str]
    created_at: datetime
    updated_at: datetime
