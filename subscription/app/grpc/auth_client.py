from __future__ import annotations

import grpc

from generated import auth_pb2
from generated import auth_pb2_grpc

from app.core.logger import logger


class AuthClient:
    """
    Async gRPC client for Auth Service.
    """

    def __init__(
        self,
        host: str = "api:50051",
    ):
        self.host = host

        self.channel = grpc.aio.insecure_channel(
            host,
        )

        self.stub = auth_pb2_grpc.AuthServiceStub(
            self.channel,
        )

        logger.info(
            "Auth gRPC client connected: %s",
            host,
        )


    async def verify_token(
        self,
        token: str,
    ) -> dict | None:

        try:

            response = await self.stub.VerifyToken(
                auth_pb2.VerifyTokenRequest(
                    token=token,
                )
            )


            if not response.valid:

                logger.warning(
                    "Auth service rejected token."
                )

                return None


            return {
                "id": response.user_id,
                "email": response.email,
                "roles": list(response.roles),
            }


        except grpc.aio.AioRpcError as exc:

            logger.exception(
                "Auth gRPC failed: %s",
                exc.details(),
            )

            return None


    async def close(self):

        await self.channel.close()

        logger.info(
            "Auth gRPC channel closed."
        )