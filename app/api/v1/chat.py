from fastapi import APIRouter, status

from app.core.logger import logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat.service import chat_service


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(request: ChatRequest):
    """
    Process a chat request.
    """

    logger.info(
        "POST /chat - Received chat request."
    )

    logger.debug(
        "Conversation=%s Message=%s",
        request.conversation_id,
        request.message,
    )

    response = await chat_service.chat(
        conversation_id=request.conversation_id,
        message=request.message,
    )

    logger.info(
        "POST /chat - Request processed."
    )

    return response


@router.get("/{task_id}")
async def get_song(task_id: str):
    """
    Get the status of a song generation task.
    """

    logger.info(
        "GET /chat/%s - Checking task status.",
        task_id,
    )

    result = await chat_service.status(task_id)

    logger.info(
        "GET /chat/%s - Status=%s",
        task_id,
        result["status"],
    )

    return result