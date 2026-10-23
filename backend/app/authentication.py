import hashlib
import hmac
import time

from backend.app.config.settings import AUTH_SESSION_MAX_AGE, AUTH_SESSION_SECRET, AUTH_USERNAME

SESSION_COOKIE_NAME = "fraud_session"


def create_session_token() -> str:
    issued_at = int(time.time())
    message = f"{AUTH_USERNAME}:{issued_at}".encode("utf-8")
    signature = hmac.new(
        AUTH_SESSION_SECRET.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return f"{issued_at}.{signature}"


def is_session_valid(token: str | None) -> bool:
    if token is None:
        return False

    try:
        issued_at_text, provided_signature = token.split(".", maxsplit=1)
        issued_at = int(issued_at_text)
    except (ValueError, TypeError):
        return False

    now = int(time.time())
    if issued_at > now or now - issued_at > AUTH_SESSION_MAX_AGE:
        return False

    message = f"{AUTH_USERNAME}:{issued_at}".encode("utf-8")
    expected_signature = hmac.new(
        AUTH_SESSION_SECRET.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(provided_signature, expected_signature)
