from pydantic import BaseModel


class MessageCreate(BaseModel):
    receiver_id: str
    content: str


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    receiver_id: str
    content: str
    created_at: str
    is_read: bool

class ConversationResponse(BaseModel):
    user_id: str
    username: str
    last_message: str
    last_message_time: str