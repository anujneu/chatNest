from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import messages_collection, users_collection
from app.dependencies.auth import get_current_user
from app.schemas.message import (
    MessageCreate,
    MessageResponse,
    ConversationResponse
)


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

@router.patch("/{user_id}/read")
def mark_messages_as_read(
    user_id: str,
    current_user=Depends(get_current_user)
):

    current_user_id = str(current_user["_id"])

    result = messages_collection.update_many(
        {
            "sender_id": user_id,
            "receiver_id": current_user_id,
            "is_read": False
        },
        {
            "$set": {
                "is_read": True
            }
        }
    )

    return {
        "message": "Messages marked as read",
        "updated_count": result.modified_count
    }

@router.get(
    "/conversations",
    response_model=list[ConversationResponse]
)
def get_conversations(
    current_user=Depends(get_current_user)
):

    current_user_id = str(current_user["_id"])

    messages = messages_collection.find({
        "$or": [
            {"sender_id": current_user_id},
            {"receiver_id": current_user_id}
        ]
    }).sort("created_at", -1)

    conversations = {}
    
    for message in messages:

        if message["sender_id"] == current_user_id:
            other_user_id = message["receiver_id"]
        else:
            other_user_id = message["sender_id"]

        if other_user_id not in conversations:

            other_user = users_collection.find_one({
                "_id": ObjectId(other_user_id)
            })

            if other_user:
                conversations[other_user_id] = {
                    "user_id": other_user_id,
                    "username": other_user["username"],
                    "last_message": message["content"],
                    "last_message_time": message["created_at"]
                }

    return list(conversations.values())



@router.get("/{user_id}", response_model=list[MessageResponse])
def get_messages(
    user_id: str,
    current_user=Depends(get_current_user)
):

    current_user_id = str(current_user["_id"])

    messages = messages_collection.find({
        "$or": [
            {
                "sender_id": current_user_id,
                "receiver_id": user_id
            },
            {
                "sender_id": user_id,
                "receiver_id": current_user_id
            }
        ]
    }).sort("created_at", 1)

    result = []

    for message in messages:
        result.append({
            "id": str(message["_id"]),
            "sender_id": message["sender_id"],
            "receiver_id": message["receiver_id"],
            "content": message["content"],
            "created_at": message["created_at"],
            "is_read": message["is_read"]
        })

    return result



