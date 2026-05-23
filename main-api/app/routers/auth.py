from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import bcrypt

from app.auth.jwt import create_access_token
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("SELECT id, email, role, password_hash FROM users WHERE email = :email"),
        {"email": form.username},
    )
    user = row.mappings().first()

    if not user or not user["password_hash"] or not bcrypt.verify(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=str(user["id"]),
        email=user["email"],
        role=user["role"],
    )
    return {"access_token": token, "token_type": "bearer"}
