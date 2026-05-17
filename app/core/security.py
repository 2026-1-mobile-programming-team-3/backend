import asyncio
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt rounds=10 = OWASP 최소 권장치. 기존 12라운드 해시는 deprecated="auto" 와 함께
# pwd_context.needs_update() 가 True 를 돌려주므로 로그인 성공 시 점진적으로 재해시된다.
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__default_rounds=10,
    bcrypt__min_rounds=10,
    deprecated="auto",
)

# bcrypt는 비밀번호 길이가 길수록 비용이 폭증하므로 상한을 둔다.
MAX_PASSWORD_LENGTH = 128

# 더미 해시는 첫 사용 시점에 lazy 계산 — 모듈 import 시 bcrypt 실행되면 콜드 스타트가 길어진다.
_DUMMY_PASSWORD_HASH: str | None = None


def _get_dummy_hash() -> str:
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = _pwd_context.hash("__dummy_password_for_timing_safety__")
    return _DUMMY_PASSWORD_HASH


def password_needs_rehash(hashed: str) -> bool:
    return _pwd_context.needs_update(hashed)


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


async def hash_password_async(plain: str) -> str:
    """bcrypt는 CPU-바운드 동기 호출이라 이벤트 루프를 막는다. 스레드로 오프로드."""
    return await asyncio.to_thread(hash_password, plain)


async def verify_password_async(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(verify_password, plain, hashed)


async def verify_dummy_password_async(plain: str) -> bool:
    """존재하지 않는 사용자 분기에서도 verify를 수행해 타이밍 누설을 차단."""
    return await asyncio.to_thread(verify_password, plain, _get_dummy_hash())


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """jose가 exp는 자동 검증. iat가 있으면 미래 발급(시계 왜곡 공격) 방지."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    iat = payload.get("iat")
    if iat is not None:
        # 60초 시계 오차는 허용
        if int(iat) > int(datetime.now(timezone.utc).timestamp()) + 60:
            raise ValueError("token issued in the future")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_hex(32)


def hash_refresh_token(raw: str) -> str:
    """JWT_SECRET_KEY를 키로 한 HMAC-SHA256. DB 유출 시 단순 SHA256보다 brute-force가 어렵다."""
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        raw.encode(),
        hashlib.sha256,
    ).hexdigest()


def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")
    if len(v) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"비밀번호는 {MAX_PASSWORD_LENGTH}자 이하여야 합니다.")
    if not re.search(r"[a-zA-Z]", v):
        raise ValueError("영문자를 포함해야 합니다.")
    if not re.search(r"\d", v):
        raise ValueError("숫자를 포함해야 합니다.")
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]', v):
        raise ValueError("특수문자를 포함해야 합니다.")
    return v


_PHONE_PATTERN = re.compile(r"^\+?[0-9\-\s]{9,20}$")


def validate_phone(v: str | None) -> str | None:
    """선택 입력. 숫자/+/-/공백만 허용, 9~20자."""
    if v is None:
        return v
    v = v.strip()
    if v == "":
        return None
    if not _PHONE_PATTERN.match(v):
        raise ValueError("연락처 형식이 올바르지 않습니다.")
    return v
