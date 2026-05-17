from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Pet
from app.schemas.pet import PetCreate, PetUpdate


async def create(db: AsyncSession, user_id: int, data: PetCreate) -> Pet:
    pet = Pet(user_id=user_id, **data.model_dump())
    db.add(pet)
    await db.commit()
    # Pet 모델의 __mapper_args__["eager_defaults"]=True 로 INSERT … RETURNING 이
    # server_default 컬럼을 미리 채워주므로 별도 refresh 불필요.
    return pet


async def get_by_id(db: AsyncSession, pet_id: int) -> Pet | None:
    result = await db.execute(select(Pet).where(Pet.id == pet_id))
    return result.scalar_one_or_none()


async def update(db: AsyncSession, pet: Pet, data: PetUpdate) -> Pet:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pet, key, value)
    pet.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pet)
    return pet


async def delete(db: AsyncSession, pet: Pet) -> None:
    await db.delete(pet)
    await db.commit()
