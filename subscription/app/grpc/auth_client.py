import grpc

from generated import auth_pb2
from generated import auth_pb2_grpc


class AuthClient:

    def __init__(
        self,
    ):
        self.channel = grpc.insecure_channel(
            "api:50051"
        )

        self.stub = (
            auth_pb2_grpc.AuthServiceStub(
                self.channel
            )
        )


    def validate_token(
        self,
        token: str,
    ):

        request = auth_pb2.AuthRequest(
            token=token
        )

        return self.stub.ValidateToken(
            request
        )