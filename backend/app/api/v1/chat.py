from typing import Annotated


from fastapi import (
    APIRouter,
    File,
    Form,
    UploadFile,
    Depends,
    status,
)


from app.core.logger import logger


from app.schemas.chat import (
    ChatResponse,
)


from app.services.chat.service import (
    chat_service,
)


from app.core.dependencies import (
    get_current_user,
)


from app.dependencies.token_guard import (
    check_token_balance,
)



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

    conversation_id: Annotated[
        str,
        Form(),
    ],


    message: Annotated[
        str | None,
        Form(),
    ] = None,


    file: Annotated[
        UploadFile | None,
        File(),
    ] = None,


    current_user=Depends(
        get_current_user
    ),


    token_context=Depends(
        check_token_balance
    ),

):


    logger.info(
        "Chat request user=%s",
        current_user["id"],
    )



    response = await chat_service.chat(

        user_id=current_user["id"],

        conversation_id=conversation_id,

        message=message,

        file=file,

        token_context=token_context,

    )



    return response








@router.get(
    "/tasks/{task_id}",
)
async def get_task_status(

    task_id:str,

    current_user=Depends(
        get_current_user
    ),

):


    return await chat_service.status(
        task_id
    )