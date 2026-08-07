from concurrent import futures

import grpc

from generated import auth_pb2
from generated import auth_pb2_grpc


class AuthService(
    auth_pb2_grpc.AuthServiceServicer
):

    def ValidateToken(
        self,
        request,
        context,
    ):
        token = request.token

        # Your existing auth validation
        user = validate_token(token)

        if not user:
            return auth_pb2.AuthResponse(
                authenticated=False
            )

        return auth_pb2.AuthResponse(
            authenticated=True,
            user_id=str(user.id),
        )


def serve():

    server = grpc.server(
        futures.ThreadPoolExecutor(
            max_workers=10
        )
    )

    auth_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthService(),
        server,
    )

    server.add_insecure_port(
        "[::]:50051"
    )

    server.start()
    server.wait_for_termination()