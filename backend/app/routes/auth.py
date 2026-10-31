from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.middleware.auth import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.schemas.common import Message
from app.utils.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    db = get_db()
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    count = await db.users.count_documents({})
    role = "admin" if count == 0 else "analyst"
    doc = {
        "name": body.name,
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "role": role,
        "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(doc)
    token, _, _ = create_token(doc["email"], role)
    return TokenResponse(access_token=token, role=role, name=doc["name"], email=doc["email"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    db = get_db()
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token, _, _ = create_token(user["email"], user["role"])
    return TokenResponse(
        access_token=token, role=user["role"], name=user["name"], email=user["email"]
    )


@router.post("/logout", response_model=Message)
async def logout(user=Depends(get_current_user)):
    db = get_db()
    exp = user.get("exp")
    await db.token_blocklist.insert_one(
        {
            "jti": user.get("jti"),
            "exp": datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc),
        }
    )
    return Message(message="Logged out")


@router.get("/me", response_model=UserPublic)
async def me(user=Depends(get_current_user)):
    return UserPublic(name=user["name"], email=user["email"], role=user["role"])
