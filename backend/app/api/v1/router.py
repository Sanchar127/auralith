from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.auth import router as auth_router

api_router = APIRouter()


api_router.include_router(chat_router)

api_router.include_router(auth_router)