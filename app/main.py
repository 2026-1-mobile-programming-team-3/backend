from pathlib import Path

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware

from app.admin.auth import AdminAuth
from app.core.rate_limit import limiter
from app.admin.views import (
    CalendarEventAdmin,
    ChatMessageAdmin,
    DeviceAdmin,
    MatchAdmin,
    MatchApplicationAdmin,
    MatchReviewAdmin,
    NotificationAdmin,
    PetAdmin,
    RefreshTokenAdmin,
    ReportAdmin,
    StoreAdmin,
    StoreReviewAdmin,
    UserAdmin,
    VolunteerRequestAdmin,
)
from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import engine
from app.web import router as web_router

API_V1_PREFIX = "/api/v1"
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="시흥가개 API",
    description="시흥시 반려동물 동반 매장 & 중성화 이동 지원 매칭 백엔드",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
)

# slowapi 등록 — 인증/신고/차단 엔드포인트에 데코레이터로 개별 제한 적용
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SessionMiddleware must be registered before Admin is mounted.
# JWT 키와 분리된 ADMIN_SESSION_KEY 사용. https_only는 운영 환경에서만 켠다 (로컬 HTTP 개발 차단 방지).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.ADMIN_SESSION_KEY,
    same_site="lax",
    https_only=settings.IS_PRODUCTION,
    max_age=60 * 60 * 8,  # 8시간
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

app.include_router(api_router, prefix=API_V1_PREFIX)
app.include_router(web_router)

# ─── SQLAdmin ────────────────────────────────────────────────────────────────
authentication_backend = AdminAuth(secret_key=settings.ADMIN_SESSION_KEY)
admin = Admin(app, engine, authentication_backend=authentication_backend, title="시흥가개 관리자")

admin.add_view(UserAdmin)
admin.add_view(DeviceAdmin)
admin.add_view(RefreshTokenAdmin)
admin.add_view(PetAdmin)
admin.add_view(NotificationAdmin)
admin.add_view(MatchAdmin)
admin.add_view(MatchApplicationAdmin)
admin.add_view(ChatMessageAdmin)
admin.add_view(MatchReviewAdmin)
admin.add_view(StoreAdmin)
admin.add_view(StoreReviewAdmin)
admin.add_view(VolunteerRequestAdmin)
admin.add_view(ReportAdmin)
admin.add_view(CalendarEventAdmin)


Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["root"])
async def health():
    return {"status": "ok"}


@app.get(f"{API_V1_PREFIX}/ping", tags=["root"])
async def ping():
    return {"ping": "pong"}
