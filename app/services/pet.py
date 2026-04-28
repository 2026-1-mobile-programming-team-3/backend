from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import pet as crud_pet
from app.models.user import Pet, User
from app.schemas.pet import PetCreate, PetUpdate


async def create_pet(db: AsyncSession, user: User, data: PetCreate) -> Pet:
    return await crud_pet.create(db, user.id, data)


async def _get_pet_or_404(db: AsyncSession, pet_id: int) -> Pet:
    pet = await crud_pet.get_by_id(db, pet_id)
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="반려동물을 찾을 수 없습니다.")
    return pet


def _check_owner(pet: Pet, user: User) -> None:
    if pet.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인의 반려동물이 아닙니다.")


async def update_pet(db: AsyncSession, user: User, pet_id: int, data: PetUpdate) -> Pet:
    pet = await _get_pet_or_404(db, pet_id)
    _check_owner(pet, user)
    return await crud_pet.update(db, pet, data)


async def delete_pet(db: AsyncSession, user: User, pet_id: int) -> None:
    pet = await _get_pet_or_404(db, pet_id)
    _check_owner(pet, user)
    await crud_pet.delete(db, pet)
