from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    APP_ENV: str = "development"

    # Railway 등 환경에서 private 도메인 URL이 따로 있을 수 있다. 있으면 우선 사용한다.
    DATABASE_PRIVATE_URL_RAW: str | None = Field(default=None, alias="DATABASE_PRIVATE_URL")
    DATABASE_URL_RAW: str | None = Field(default=None, alias="DATABASE_URL")

    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    # DB 커넥션 풀 — 운영에서는 동시 요청 대비 넉넉히. asyncpg는 한 connection 당 한 쿼리.
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_SECONDS: int = 300  # 5분마다 connection 재활용 — Railway 의 idle TCP 차단 회피

    # Redis도 DB와 동일하게 private 도메인을 우선 사용. 환경에 따라 정의되지 않을 수 있어 옵션.
    REDIS_PRIVATE_URL_RAW: str | None = Field(default=None, alias="REDIS_PRIVATE_URL")
    REDIS_URL_RAW: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

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
    KAKAO_REST_API_KEY: str
    NEWS_CACHE_TTL: int = 3600  # 1시간 (이전 4시간 → 단축)

    # Firebase Cloud Messaging (선택). 둘 다 미설정이면 FCM 푸시는 no-op.
    # - FIREBASE_CREDENTIALS_PATH: 로컬 파일 경로 (개발/로컬)
    # - FIREBASE_CREDENTIALS_JSON: 서비스 계정 JSON 전체를 문자열로 (Railway 등 PaaS)
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_CREDENTIALS_JSON: str | None = None

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
    def REDIS_URL(self) -> str:
        # private domain이 정의돼 있고 placeholder가 남아있지 않으면 그쪽을 사용.
        priv = self.REDIS_PRIVATE_URL_RAW
        if priv and "${{" not in priv:
            return priv
        return self.REDIS_URL_RAW

    @staticmethod
    def _normalize_pg_url(url: str) -> str:
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def DATABASE_URL(self) -> str:
        # 우선순위: 1) DATABASE_PRIVATE_URL (Railway internal 도메인 → 한 자릿수 ms RTT)
        #          2) DATABASE_URL (public proxy 가능성 — 매 연결마다 외부 hop)
        #          3) POSTGRES_USER/PASSWORD/DB (로컬 docker compose 등)
        raw = self.DATABASE_PRIVATE_URL_RAW or self.DATABASE_URL_RAW
        if raw:
            return self._normalize_pg_url(raw)
        if not (self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB):
            raise ValueError(
                "DATABASE_PRIVATE_URL / DATABASE_URL / POSTGRES_USER+PASSWORD+DB 중 하나는 설정해야 합니다."
            )
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
