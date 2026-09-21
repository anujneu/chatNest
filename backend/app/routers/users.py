from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.schemas.user import UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):

    return {
        "id": str(current_user["_id"]),
        "username": current_user["username"],
        "email": current_user["email"]
    }