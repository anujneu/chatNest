from fastapi import APIRouter, HTTPException
from app.database import users_collection
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.utils.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate):

    existing_user = users_collection.find_one({
        "email": user.email
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    hashed_password = hash_password(user.password)

    user_data = {
        "username": user.username,
        "email": user.email,
        "password": hashed_password
    }

    result = users_collection.insert_one(user_data)

    return {
        "id": str(result.inserted_id),
        "username": user.username,
        "email": user.email
    }

@router.post("/login")
def login(user: UserLogin):

    existing_user = users_collection.find_one({
        "email": user.email
    })

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_correct = verify_password(
        user.password,
        existing_user["password"]
    )

    if not password_correct:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "user_id": str(existing_user["_id"])
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }