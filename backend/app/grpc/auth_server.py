from __future__ import annotations

import grpc

from jose import JWTError

from generated import auth_pb2
from generated import auth_pb2_grpc

from app.core.logger import logger
from app.core.security import verify_access_token
from app.db.session import AsyncSessionLocal
from app.repositories.user import UserRepository


class AuthService(
    auth_pb2_grpc.AuthServiceServicer,
):
    """
    Authentication gRPC service.

    Used by internal microservices
    to validate JWT access tokens.
    """

    async def VerifyToken(
        self,
        request,
        context,
    ):
        """
        Verify JWT token and return user information.
        """

        logger.info(
            "gRPC VerifyToken request received."
        )

        # ----------------------------------------------
        # Validate JWT
        # ----------------------------------------------

        try:
            payload = verify_access_token(
                request.token,
            )

            user_id = payload["sub"]

            logger.debug(
                "JWT verified successfully. user_id=%s",
                user_id,
            )

        except JWTError:

            logger.warning(
                "Invalid JWT received."
            )

            return auth_pb2.VerifyTokenResponse(
                valid=False,
            )

        except Exception:

            logger.exception(
                "Unexpected JWT validation error."
            )

            return auth_pb2.VerifyTokenResponse(
                valid=False,
            )


        # ----------------------------------------------
        # Fetch User
        # ----------------------------------------------

        try:

            async with AsyncSessionLocal() as db:

                repo = UserRepository(db)

                user = await repo.get_by_id(
                    user_id,
                )


                if user is None:

                    logger.warning(
                        "User not found. user_id=%s",
                        user_id,
                    )

                    return auth_pb2.VerifyTokenResponse(
                        valid=False,
                    )


                logger.info(
                    "User authenticated successfully. user_id=%s",
                    user.id,
                )


                roles = [
                    "admin"
                    if getattr(
                        user,
                        "is_admin",
                        False,
                    )
                    else "user"
                ]


                return auth_pb2.VerifyTokenResponse(
                    valid=True,
                    user_id=str(user.id),
                    email=user.email,
                    roles=roles,
                )


        except Exception:

            logger.exception(
                "Database error while validating token."
            )

            return auth_pb2.VerifyTokenResponse(
                valid=False,
            )



async def serve():
    """
    Start Authentication gRPC server.
    """

    logger.info(
        "Starting Authentication gRPC server..."
    )


    server = grpc.aio.server()


    auth_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthService(),
        server,
    )


    address = "[::]:50051"


    server.add_insecure_port(
        address,
    )


    await server.start()


    logger.info(
        "Authentication gRPC server listening on %s",
        address,
    )


    await server.wait_for_termination()