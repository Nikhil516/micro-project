from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_db
from app.utils.security import decode_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    db = get_db()
    blocked = await db.token_blocklist.find_one({"jti": payload.get("jti")})
    if blocked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revoked")
    user = await db.users.find_one({"email": payload["sub"]})
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    user["jti"] = payload.get("jti")
    user["exp"] = payload.get("exp")
    return user


def require_roles(*roles: str):
    async def _inner(user=Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return _inner
