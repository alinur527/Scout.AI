from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select

from app.models.entities import User, utcnow

passwords = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def session(request: Request):
    with request.app.state.sessions() as db:
        yield db


def current_user(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(session)
):
    unauthorized = HTTPException(401, "Please log in again", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    settings = request.app.state.settings
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
        user = db.scalar(select(User).where(User.id == int(payload["sub"])))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise unauthorized from None
    if user is None:
        raise unauthorized
    return user


def player_user(user=Depends(current_user)):
    if user.role != "player":
        raise HTTPException(403, "This action requires a player account")
    return user


def scout_user(user=Depends(current_user)):
    if user.role not in ("scout", "admin"):
        raise HTTPException(403, "This action requires a scout account")
    return user


def token_for(user, settings):
    now = utcnow()
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
