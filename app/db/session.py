import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session as SyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

# pool_pre_ping=True: Railway 가 idle TCP 를 끊으면 풀의 stale connection 이 실제 쿼리에서
#                     1~2초씩 행 거는 사례를 막는다. 체크아웃마다 SELECT 1 한 번이 internal
#                     네트워크에서는 한 자릿수 ms 라 트레이드오프가 명확하게 유리.
# pool_recycle:       idle 이 길어진 connection 을 자연 폐기. Railway 가 ~몇 분 후 끊는
#                     경향이 있어 settings 기본을 짧게 (5분).
# pool_size + max_overflow: 동시 요청 대비 풀 여유.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
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
