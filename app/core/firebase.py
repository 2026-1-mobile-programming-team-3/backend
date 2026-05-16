"""Firebase Cloud Messaging 클라이언트.

서비스 계정 키가 미설정이면 모든 함수가 no-op + 1회 안내 로그.
요청 경로에서 FCM 응답을 기다리지 않도록 호출은 fire-and-forget으로 설계 (db/session.py의 after_commit 훅).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_init_attempted: bool = False
_app: Any = None  # firebase_admin.App | None


def _try_init() -> None:
    global _init_attempted, _app
    if _init_attempted:
        return
    _init_attempted = True

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning(
            "firebase-admin 패키지가 설치되어 있지 않습니다. "
            "requirements.txt 에 firebase-admin 을 추가하거나 FCM 푸시를 의도적으로 비활성화하세요."
        )
        return

    from app.core.config import settings

    json_blob = settings.FIREBASE_CREDENTIALS_JSON
    cred_path = settings.FIREBASE_CREDENTIALS_PATH

    cred = None
    if json_blob:
        try:
            cred = credentials.Certificate(json.loads(json_blob))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("FIREBASE_CREDENTIALS_JSON 파싱 실패: %s", exc)
            return
    elif cred_path:
        path = Path(cred_path)
        if not path.is_file():
            logger.warning(
                "FIREBASE_CREDENTIALS_PATH 가 가리키는 파일이 없습니다: %s — FCM 푸시 비활성화.",
                path,
            )
            return
        cred = credentials.Certificate(str(path))
    else:
        logger.info(
            "FIREBASE_CREDENTIALS_PATH / FIREBASE_CREDENTIALS_JSON 미설정 — FCM 푸시는 no-op."
        )
        return

    try:
        _app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK 초기화 완료.")
    except ValueError:
        # 이미 초기화된 경우(테스트 재실행 등) 기본 앱 재사용.
        _app = firebase_admin.get_app()


def is_ready() -> bool:
    _try_init()
    return _app is not None


def send_to_tokens(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> list[str]:
    """토큰 목록에 동기적으로 푸시 발송. 무효(unregistered/not-found) 토큰 목록 반환.

    호출자는 반환된 무효 토큰을 DB(devices.fcm_token)에서 정리해야 한다.
    `firebase_admin` 호출은 blocking 이므로 async 컨텍스트에서는 `asyncio.to_thread` 로 감싸 호출.
    """
    if not tokens or not is_ready():
        return []

    from firebase_admin import messaging

    # data payload 의 값은 문자열만 허용.
    safe_data: dict[str, str] = {
        k: ("" if v is None else str(v)) for k, v in (data or {}).items()
    }
    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data=safe_data,
        android=messaging.AndroidConfig(priority="high"),
    )

    try:
        resp = messaging.send_each_for_multicast(message)
    except Exception:
        logger.exception("FCM 전송 실패 (multicast).")
        return []

    invalid: list[str] = []
    for token, r in zip(tokens, resp.responses):
        if r.exception is None:
            continue
        code = getattr(r.exception, "code", "") or ""
        message_str = str(r.exception)
        if (
            code in ("UNREGISTERED", "INVALID_ARGUMENT", "NOT_FOUND")
            or "Requested entity was not found" in message_str
        ):
            invalid.append(token)
        else:
            logger.warning(
                "FCM 부분 실패 (token=%s…): code=%s err=%s",
                token[:12],
                code,
                message_str,
            )
    return invalid
