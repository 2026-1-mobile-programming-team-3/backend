from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    blocks,
    chats,
    favorites,
    geo,
    home,
    maps,
    matches,
    news,
    notifications,
    pets,
    reports,
    store_requests,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(pets.router)
api_router.include_router(news.router)
api_router.include_router(maps.router)
api_router.include_router(store_requests.router)
api_router.include_router(matches.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(blocks.router)
api_router.include_router(home.router)
api_router.include_router(geo.router)
api_router.include_router(favorites.router)
api_router.include_router(chats.router)
api_router.include_router(admin.router)
