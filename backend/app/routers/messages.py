from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import messages_collection, users_collection
from app.dependencies.auth import get_current_user
from app.schemas.message import MessageCreate, MessageResponse


router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

@router.post("/", response_model=MessageResponse)
def send_message(
    message: MessageCreate,
    current_user=Depends(get_current_user)
):

    receiver = users_collection.find_one({
        "_id": ObjectId(message.receiver_id)
    })

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    message_data = {
        "sender_id": str(current_user["_id"]),
        "receiver_id": message.receiver_id,
        "content": message.content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_read": False
    }

    result = messages_collection.insert_one(message_data)

    return {
        "id": str(result.inserted_id),
        **message_data
    }