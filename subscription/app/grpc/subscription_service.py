from generated import subscription_pb2
from generated import subscription_pb2_grpc

class SubscriptionService(
    subscription_pb2_grpc.SubscriptionServiceServicer,
):
    """
    gRPC implementation for subscription operations.
    """

    def GetSubscription(self, request, context):
        """
        Dummy implementation.

        Later:
        - Query PostgreSQL
        - Check active subscription
        - Return remaining tokens
        """

        print(f"Received request for user: {request.user_id}")

        return subscription_pb2.SubscriptionResponse(
            active=True,
            remaining_tokens=5000,
        )