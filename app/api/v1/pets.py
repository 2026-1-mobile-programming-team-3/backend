from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.pet import PetCreate, PetResponse, PetUpdate
from app.services import pet as pet_service

router = APIRouter(prefix="/users/me/pets", tags=["pets"])


@router.post("", response_model=PetResponse, status_code=201)
async def create_pet(
    data: PetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await pet_service.create_pet(db, current_user, data)


@router.patch("/{pet_id}", response_model=PetResponse)
async def update_pet(
    pet_id: int,
    data: PetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await pet_service.update_pet(db, current_user, pet_id, data)


@router.delete("/{pet_id}", status_code=204)
async def delete_pet(
    pet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await pet_service.delete_pet(db, current_user, pet_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
