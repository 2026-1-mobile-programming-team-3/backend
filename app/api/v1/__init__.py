from fastapi import APIRouter

from app.api.v1 import auth, news, pets, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(pets.router)
api_router.include_router(news.router)
