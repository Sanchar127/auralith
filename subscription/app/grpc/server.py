import grpc
from concurrent import futures

from generated import subscription_pb2
from generated import subscription_pb2_grpc


from app.services.wallet import WalletService
from app.db.session import AsyncSessionLocal



class SubscriptionGrpcService(
    subscription_pb2_grpc.SubscriptionServiceServicer
):


    async def GetWallet(
        self,
        request,
        context,
    ):


        async with AsyncSessionLocal() as db:


            service = WalletService(db)


            wallet = await service.get_wallet(
                request.user_id
            )



            if wallet is None:

                return subscription_pb2.WalletResponse(
                    user_id=request.user_id,
                    available_tokens=0,
                    lifetime_used_tokens=0,
                )



            return subscription_pb2.WalletResponse(

                user_id=str(wallet.user_id),

                available_tokens=
                    wallet.available_tokens,


                lifetime_used_tokens=
                    wallet.lifetime_used_tokens,

            )





    async def ConsumeTokens(
        self,
        request,
        context,
    ):


        async with AsyncSessionLocal() as db:


            service = WalletService(db)



            wallet = await service.consume_tokens(

                user_id=request.user_id,

                amount=request.total_tokens,

            )



            return subscription_pb2.TokenConsumeResponse(

                success=True,

                remaining_tokens=
                    wallet.available_tokens,


                message="Tokens consumed",

            )



async def serve():
    print("Starting gRPC server...")

    server = grpc.aio.server()

    subscription_pb2_grpc.add_SubscriptionServiceServicer_to_server(
        SubscriptionGrpcService(),
        server,
    )

    server.add_insecure_port("[::]:50052")

    await server.start()

    print("gRPC server listening on :50052")

    await server.wait_for_termination()