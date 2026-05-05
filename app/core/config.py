from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    APP_ENV: str = "development"

    DATABASE_URL_RAW: str | None = Field(default=None, alias="DATABASE_URL")

    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    # 어드민 세션 쿠키 서명용 키. 미지정 시 JWT_SECRET_KEY 재사용을 막기 위해 검증 단계에서 차단.
    ADMIN_SESSION_SECRET: str | None = None

    # 어드민 로그인 실패 잠금 (per-IP). Redis로 저장.
    ADMIN_LOGIN_MAX_ATTEMPTS: int = 5
    ADMIN_LOGIN_LOCKOUT_SECONDS: int = 900  # 15분

    NAVER_API_ID: str
    NAVER_API_SECRET: str
    NEWS_CACHE_TTL: int = 14_400  # 4시간

    @property
    def ADMIN_SESSION_KEY(self) -> str:
        """ADMIN_SESSION_SECRET가 설정돼 있으면 그것을, 없으면 JWT 키 + 고정 솔트로 분리."""
        if self.ADMIN_SESSION_SECRET:
            return self.ADMIN_SESSION_SECRET
        # JWT_SECRET_KEY를 그대로 쓰지 않도록 도메인 솔트를 덧붙인다.
        return f"{self.JWT_SECRET_KEY}::admin-session"

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    @model_validator(mode="after")
    def _validate_runtime_invariants(self) -> "Settings":
        if self.NEWS_CACHE_TTL <= 0:
            raise ValueError("NEWS_CACHE_TTL은 0보다 커야 합니다 (초 단위).")
        if self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES는 0보다 커야 합니다.")
        if self.JWT_REFRESH_TOKEN_EXPIRE_DAYS <= 0:
            raise ValueError("JWT_REFRESH_TOKEN_EXPIRE_DAYS는 0보다 커야 합니다.")
        if self.ADMIN_LOGIN_MAX_ATTEMPTS <= 0:
            raise ValueError("ADMIN_LOGIN_MAX_ATTEMPTS는 1 이상이어야 합니다.")
        return self

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_RAW:
            url = self.DATABASE_URL_RAW
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        if not (self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB):
            raise ValueError("DATABASE_URL or POSTGRES_USER/PASSWORD/DB must be set")
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
