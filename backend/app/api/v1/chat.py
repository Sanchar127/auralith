from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)

from app.core.dependencies import get_current_user
from app.dependencies.token_guard import check_token_balance
from app.schemas.chat import ChatResponse
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
async def chat(
    message: Annotated[
        str | None,
        Form(description="User message"),
    ] = None,

    conversation_id: Annotated[
        UUID | None,
        Form(
            description=(
                "Existing conversation ID. "
                "Leave empty to create a new conversation."
            )
        ),
    ] = None,

    file: Annotated[
        UploadFile | None,
        File(),
    ] = None,

    current_user=Depends(get_current_user),

    token_context=Depends(check_token_balance),
):
    user_id = str(current_user.id)

    response = await chat_service.chat(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        file=file,
        token_context=token_context,
    )

    return response


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)

    return await chat_service.status(
        task_id=task_id,
        user_id=user_id,
    )