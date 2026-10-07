from datetime import datetime, timezone
import json

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect
)

from app.connection_manager import ConnectionManager
from app.database import messages_collection, users_collection
from app.dependencies.auth import (
    get_current_user,
    get_user_from_token
)
from app.schemas.message import (
    MessageCreate,
    MessageResponse,
    ConversationResponse
)


router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

manager = ConnectionManager()


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


@router.get(
    "/{user_id}",
    response_model=list[MessageResponse]
)
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


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        current_user = get_user_from_token(token)

    except Exception:
        await websocket.close(code=1008)
        return

    user_id = str(current_user["_id"])

    await manager.connect(user_id, websocket)

    try:

        while True:

            data = await websocket.receive_text()

            print("Received:", data)

            try:
                message_data = json.loads(data)

                receiver_id = message_data["receiver_id"]
                content = message_data["content"]

            except Exception as e:

                print("Invalid message:", e)

                await websocket.send_text(
                    json.dumps({
                        "status": "error",
                        "message": "Invalid message format"
                    })
                )

                continue

            try:

                receiver = users_collection.find_one({
                    "_id": ObjectId(receiver_id)
                })

            except Exception:

                await websocket.send_text(
                    json.dumps({
                        "status": "error",
                        "message": "Invalid receiver ID"
                    })
                )

                continue

            if not receiver:

                await websocket.send_text(
                    json.dumps({
                        "status": "error",
                        "message": "Receiver not found"
                    })
                )

                continue

            new_message={
                "sender_id": user_id,
                "receiver_id": receiver_id,
                "content": content,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "is_delivered": False,
                "is_read": False
            }

            result = messages_collection.insert_one(
                new_message
            )

            message_response = {
                "id": str(result.inserted_id),
                "sender_id": new_message["sender_id"],
                "receiver_id": new_message["receiver_id"],
                "content": new_message["content"],
                "created_at": new_message["created_at"],
                "is_delivered": False,
                "is_read": False
            }

            sent = await manager.send_personal_message(
                json.dumps(message_response),
                receiver_id
            )

            if sent:

                messages_collection.update_one(
                    {"_id": result.inserted_id},
                    {
                        "$set": {
                            "is_delivered": True
                        }
                    }
                )

                await websocket.send_text(
                    json.dumps({
                        "status": "delivered",
                        "message_id": message_response["id"]
                    })
                )

            else:

                await websocket.send_text(
                    json.dumps({
                        "status": "saved",
                        "message_id": message_response["id"]
                    })
                )

    except WebSocketDisconnect:

        manager.disconnect(user_id)

        print(
            f"{current_user['username']} disconnected"
        )