import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session as SyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

# pool_pre_ping=False: 매 체크아웃 시의 SELECT 1 라운드트립 제거.
# pool_recycle: 일정 시간이 지난 connection은 폐기 → 끊긴 idle connection을 자연스럽게 갱신.
# pool_size + max_overflow: 동시 요청 대비 풀 여유. 기본(5+10)은 idle 요청 큐잉을 유발.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=False,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ─── post-commit 후크 ────────────────────────────────────────────────────────
# notification.enqueue() 가 세션의 info 에 "pending_pushes" 클로저를 누적해두면,
# 트랜잭션 커밋이 성공한 직후 fire-and-forget 으로 FCM 발송을 스케줄한다.
# 실패해도 응답 경로에는 영향이 없도록 모두 background task 로 처리.


@event.listens_for(SyncSession, "after_commit")
def _fire_pending_pushes(session: SyncSession) -> None:
    pushes = session.info.pop("pending_pushes", None)
    if not pushes:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # alembic CLI 등 이벤트 루프가 없는 컨텍스트 — 푸시 스킵.
        return
    for coro_factory in pushes:
        try:
            loop.create_task(coro_factory())
        except Exception:
            logger.exception("FCM 푸시 스케줄 실패")


@event.listens_for(SyncSession, "after_rollback")
def _drop_pending_pushes(session: SyncSession) -> None:
    session.info.pop("pending_pushes", None)
