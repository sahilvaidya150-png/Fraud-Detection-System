import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from backend.app.authentication import SESSION_COOKIE_NAME, create_session_token, is_session_valid
from backend.app.config.settings import (
    AUTH_COOKIE_SECURE,
    AUTH_PASSWORD,
    AUTH_SESSION_MAX_AGE,
    AUTH_USERNAME,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


@router.post("/login")
def login(credentials: LoginRequest, response: Response) -> dict[str, str | bool]:
    username_matches = hmac.compare_digest(
        credentials.username.encode("utf-8"),
        AUTH_USERNAME.encode("utf-8"),
    )
    password_matches = hmac.compare_digest(
        credentials.password.encode("utf-8"),
        AUTH_PASSWORD.encode("utf-8"),
    )
    if not username_matches or not password_matches:
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(),
        max_age=AUTH_SESSION_MAX_AGE,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "username": AUTH_USERNAME}


@router.get("/session")
def get_session(request: Request) -> dict[str, str | bool]:
    if not is_session_valid(request.cookies.get(SESSION_COOKIE_NAME)):
        return {"authenticated": False}
    return {"authenticated": True, "username": AUTH_USERNAME}


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"authenticated": False}
