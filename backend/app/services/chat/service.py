from fastapi import (
    UploadFile,
    HTTPException,
)

from celery.result import AsyncResult


from app.core.logger import logger


from app.grpc.subscription_client import (
    SubscriptionClient,
)


from app.schemas.chat import (
    ChatResponse,
)


from app.services.rag.pipeline import (
    rag_pipeline,
)


from app.services.token.token_counter import (
    token_counter,
)





class ChatService:


    def __init__(self):

        self.subscription_client = (
            SubscriptionClient()
        )





    async def chat(

        self,

        user_id:str,

        conversation_id:str,

        message:str | None,

        file:UploadFile | None = None,

        token_context:dict | None = None,

    ):



        logger.info(
            "Processing chat user=%s",
            user_id,
        )



        #
        # 1. Count input tokens
        #

        input_tokens = token_counter.count(
            message or ""
        )



        #
        # 2. Run AI
        #

        try:

            response = await rag_pipeline.run(

                conversation_id=

                    conversation_id,


                message=

                    message or "",

            )


        except Exception as exc:

            logger.exception(
                "AI generation failed"
            )

            raise HTTPException(
                500,
                "AI generation failed",
            ) from exc





        #
        # 3. Count output tokens
        #

        output_tokens = token_counter.count(
            response
        )



        total_tokens = (

            input_tokens

            +

            output_tokens

        )





        #
        # 4. Consume tokens
        #

        try:


            await self.subscription_client.consume_tokens(

                user_id=user_id,


                input_tokens=input_tokens,


                output_tokens=output_tokens,


                total_tokens=total_tokens,


                model="llama3",


            )



        except Exception as exc:


            logger.exception(
                "Token deduction failed"
            )


            raise HTTPException(

                status_code=503,

                detail="Token service unavailable",

            ) from exc





        return ChatResponse(

            success=True,

            type="chat",

            conversation_id=conversation_id,

            message=response,

        )







    async def status(
        self,
        task_id:str,
    ):


        task = AsyncResult(
            task_id
        )


        return {

            "task_id": task.id,


            "status": task.status,


            "result":
                task.result
                if task.ready()
                else None,

        }





chat_service = ChatService()