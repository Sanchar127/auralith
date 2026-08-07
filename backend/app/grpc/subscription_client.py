import grpc

from generated import subscription_pb2
from generated import subscription_pb2_grpc

class SubscriptionClient:
    def __init__(self):
        self.channel = grpc.insecure_channel("subscription:50051")
        self.stub = subscription_pb2_grpc.SubscriptionServiceStub(
            self.channel
        )

    def get_subscription(self, user_id: str):
        request = subscription_pb2.GetSubscriptionRequest(
            user_id=user_id,
        )

        return self.stub.GetSubscription(request)