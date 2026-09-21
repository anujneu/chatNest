from fastapi import FastAPI

from app.database import client
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.messages import router as messages_router


app = FastAPI(title="ChatNest API")


@app.get("/")
def home():
    return {"message": "ChatNest API is running"}


@app.get("/test-db")
def test_database():
    try:
        client.admin.command("ping")
        return {"message": "MongoDB connected successfully"}
    except Exception as e:
        return {"error": str(e)}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(messages_router)