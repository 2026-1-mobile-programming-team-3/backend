from pathlib import Path

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from app.admin.auth import AdminAuth
from app.core.deps import close_redis
from app.core.rate_limit import limiter
from app.admin.views import (
    CalendarEventAdmin,
    ChatMessageAdmin,
    ChatRoomAdmin,
    DeviceAdmin,
    MatchAdmin,
    MatchApplicationAdmin,
    MatchReviewAdmin,
    NotificationAdmin,
    NotificationSettingAdmin,
    PetAdmin,
    RefreshTokenAdmin,
    ReportAdmin,
    StoreAdmin,
    StoreFavoriteAdmin,
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

# 응답 자동 압축 — 500B 이상의 응답에 대해 gzip 적용. preview-app.js 같은 정적 자산도 포함.
app.add_middleware(GZipMiddleware, minimum_size=500)

# SessionMiddleware must be registered before Admin is mounted.
# JWT 키와 분리된 ADMIN_SESSION_KEY 사용. https_only는 운영 환경에서만 켠다 (로컬 HTTP 개발 차단 방지).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.ADMIN_SESSION_KEY,
    same_site="lax",
    https_only=settings.IS_PRODUCTION,
    max_age=60 * 60 * 8,  # 8시간
)

class CachedStaticFiles(StaticFiles):
    """짧은 캐시 헤더를 붙이는 StaticFiles. HTML 은 캐시하지 않고 그 외 자산은 5분 캐시."""

    def __init__(self, *args, max_age: int = 300, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._max_age = max_age

    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        ctype = response.headers.get("content-type", "")
        if ctype.startswith("text/html"):
            # HTML 은 새 배포가 바로 보이도록 캐시 금지
            response.headers["Cache-Control"] = "no-cache"
        else:
            response.headers["Cache-Control"] = f"public, max-age={self._max_age}"
        return response


app.mount(
    "/static",
    CachedStaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

# Branch 2 — 모바일 앱 미리보기 (gagae-design/v2 모방). 정적 서빙만.
app.mount(
    "/preview",
    CachedStaticFiles(directory=str(BASE_DIR / "static" / "preview"), html=True),
    name="preview",
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
admin.add_view(NotificationSettingAdmin)
admin.add_view(MatchAdmin)
admin.add_view(MatchApplicationAdmin)
admin.add_view(ChatRoomAdmin)
admin.add_view(ChatMessageAdmin)
admin.add_view(MatchReviewAdmin)
admin.add_view(StoreAdmin)
admin.add_view(StoreFavoriteAdmin)
admin.add_view(StoreReviewAdmin)
admin.add_view(VolunteerRequestAdmin)
admin.add_view(ReportAdmin)
admin.add_view(CalendarEventAdmin)


Instrumentator().instrument(app).expose(app)


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    # 싱글톤 Redis 풀 정리.
    await close_redis()


@app.get("/health", tags=["root"])
async def health():
    return {"status": "ok"}


@app.get(f"{API_V1_PREFIX}/ping", tags=["root"])
async def ping():
    return {"ping": "pong"}
