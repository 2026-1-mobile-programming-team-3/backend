from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    blocks,
    maps,
    matches,
    news,
    notifications,
    pets,
    reports,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(pets.router)
api_router.include_router(news.router)
api_router.include_router(maps.router)
api_router.include_router(matches.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(blocks.router)
api_router.include_router(admin.router)
