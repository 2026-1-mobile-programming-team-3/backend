from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

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
