from celery.result import AsyncResult

from app.core.logger import logger
from app.schemas.chat import ChatResponse
from app.tasks.song import generate_song

from app.services.chat.intent import intent_classifier
from app.services.rag.pipeline import rag_pipeline


class ChatService:
    """
    Main orchestration service.

    Responsible for routing a request to either:

    - Song Generation
    - RAG Conversation
    """

    async def chat(
        self,
        conversation_id: str,
        message: str,
    ) -> ChatResponse:

        logger.info(
            "Received chat request."
        )

        # ---------------------------------------
        # Detect user intent
        # ---------------------------------------

        intent = await intent_classifier.classify(
            message
        )

        logger.info(
            "Detected intent=%s",
            intent,
        )

        # ---------------------------------------
        # SONG GENERATION
        # ---------------------------------------

        if intent == "song":

            task = generate_song.delay(
                message
            )

            logger.info(
                "Song generation queued. task_id=%s",
                task.id,
            )

            return ChatResponse(
                success=True,
                type="song",
                conversation_id=conversation_id,
                task_id=task.id,
                status="queued",
            )

        # ---------------------------------------
        # RAG CHAT
        # ---------------------------------------

        logger.info(
            "Running RAG pipeline..."
        )

        response = await rag_pipeline.run(
            conversation_id=conversation_id,
            message=message,
        )

        logger.info(
            "RAG response generated."
        )

        return ChatResponse(
            success=True,
            type="chat",
            conversation_id=conversation_id,
            message=response,
        )

    async def status(
        self,
        task_id: str,
    ):

        logger.info(
            "Checking task status. task_id=%s",
            task_id,
        )

        task = AsyncResult(task_id)

        return {
            "task_id": task.id,
            "status": task.status,
            "result": (
                task.result
                if task.ready()
                else None
            ),
        }


chat_service = ChatService()