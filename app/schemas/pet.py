from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.enums import PetSpecies


class PetCreate(BaseModel):
    name: str
    species: PetSpecies
    breed: Optional[str] = None
    age: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    is_neutered: bool
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
    # api-spec 1.10: 수정 가능 필드는 is_neutered, weight_kg 만
    is_neutered: Optional[bool] = None
    weight_kg: Optional[Decimal] = None

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
    photo_url: Optional[str]
    created_at: datetime
    updated_at: datetime
