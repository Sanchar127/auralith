
from __future__ import annotations

import grpc

from app.core.config import settings
from app.core.logger import logger

from generated import (
    deepfilter_pb2,
    deepfilter_pb2_grpc,
)


class DeepFilterClient:
    """
    gRPC client for the DeepFilterNet microservice.

    The backend sends MinIO object references rather than
    transferring audio bytes through gRPC.

    Flow:

        Backend
            |
            | gRPC
            v
        DeepFilterNet
            |
            +--> Download input from MinIO
            |
            +--> Enhance audio
            |
            +--> Upload output to MinIO
            |
            v
        Response
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ) -> None:

        self.host = (
            host
            or getattr(
                settings,
                "DEEPFILTER_HOST",
                "deepfilter",
            )
        )

        self.port = (
            port
            or getattr(
                settings,
                "DEEPFILTER_PORT",
                50051,
            )
        )

        self.target = (
            f"{self.host}:{self.port}"
        )

        self.channel: grpc.aio.Channel | None = None

        self.stub: (
            deepfilter_pb2_grpc.DeepFilterServiceStub
            | None
        ) = None

    # =========================================================
    # Connection
    # =========================================================

    def _get_stub(
        self,
    ) -> deepfilter_pb2_grpc.DeepFilterServiceStub:

        if self.channel is None:

            logger.info(
                "Connecting to DeepFilter service "
                "target=%s",
                self.target,
            )

            self.channel = grpc.aio.insecure_channel(
                self.target
            )

            self.stub = (
                deepfilter_pb2_grpc
                .DeepFilterServiceStub(
                    self.channel
                )
            )

        return self.stub

    # =========================================================
    # Enhance Audio
    # =========================================================

    async def enhance_audio(
        self,
        *,
        job_id: str,
        user_id: str,
        conversation_id: str,
        input_bucket: str,
        input_object_key: str,
        output_bucket: str,
        output_object_key: str,
        noise_reduction: bool = True,
        dereverberation: bool = False,
        gain_normalization: bool = True,
        sample_rate: int = 0,
        channels: int = 0,
        output_format: str = "wav",
        bitrate: int = 0,
        metadata: dict[str, str] | None = None,
    ) -> deepfilter_pb2.EnhanceAudioResponse:
        """
        Request audio enhancement from DeepFilterNet.

        Audio itself is NOT sent through gRPC.

        Only MinIO bucket/object references are sent.
        """

        stub = self._get_stub()

        options = (
            deepfilter_pb2.AudioEnhancementOptions(
                noise_reduction=noise_reduction,
                dereverberation=dereverberation,
                gain_normalization=gain_normalization,
                sample_rate=sample_rate,
                channels=channels,
                output_format=output_format,
                bitrate=bitrate,
            )
        )

        request = (
            deepfilter_pb2.EnhanceAudioRequest(
                job_id=job_id,
                user_id=user_id,
                conversation_id=conversation_id,
                input_bucket=input_bucket,
                input_object_key=input_object_key,
                output_bucket=output_bucket,
                output_object_key=output_object_key,
                options=options,
                metadata=metadata or {},
            )
        )

        logger.info(
            "Sending audio enhancement request "
            "to DeepFilter. "
            "job_id=%s input=%s output=%s",
            job_id,
            input_object_key,
            output_object_key,
        )

        try:

            response = await stub.EnhanceAudio(
                request
            )

        except grpc.aio.AioRpcError as exc:

            logger.error(
                "DeepFilter gRPC request failed "
                "job_id=%s code=%s details=%s",
                job_id,
                exc.code(),
                exc.details(),
            )

            raise

        logger.info(
            "DeepFilter response received "
            "job_id=%s status=%s output=%s",
            response.job_id,
            response.status,
            response.output_object_key,
        )

        return response

    # =========================================================
    # Get Job Status
    # =========================================================

    async def get_job_status(
        self,
        *,
        job_id: str,
    ) -> deepfilter_pb2.GetJobStatusResponse:
        """
        Ask DeepFilterNet for the current processing status.
        """

        stub = self._get_stub()

        request = (
            deepfilter_pb2.GetJobStatusRequest(
                job_id=job_id,
            )
        )

        logger.debug(
            "Requesting DeepFilter job status "
            "job_id=%s",
            job_id,
        )

        try:

            response = await stub.GetJobStatus(
                request
            )

        except grpc.aio.AioRpcError as exc:

            logger.error(
                "DeepFilter status request failed "
                "job_id=%s code=%s details=%s",
                job_id,
                exc.code(),
                exc.details(),
            )

            raise

        return response

    # =========================================================
    # Cancel Job
    # =========================================================

    async def cancel_job(
        self,
        *,
        job_id: str,
    ) -> deepfilter_pb2.CancelJobResponse:
        """
        Request cancellation of a DeepFilter job.
        """

        stub = self._get_stub()

        request = (
            deepfilter_pb2.CancelJobRequest(
                job_id=job_id,
            )
        )

        logger.info(
            "Requesting DeepFilter job cancellation "
            "job_id=%s",
            job_id,
        )

        try:

            response = await stub.CancelJob(
                request
            )

        except grpc.aio.AioRpcError as exc:

            logger.error(
                "DeepFilter cancellation failed "
                "job_id=%s code=%s details=%s",
                job_id,
                exc.code(),
                exc.details(),
            )

            raise

        return response

    # =========================================================
    # Health Check
    # =========================================================

    async def health_check(
        self,
    ) -> deepfilter_pb2.HealthCheckResponse:
        """
        Check whether the DeepFilter service is healthy.
        """

        stub = self._get_stub()

        request = (
            deepfilter_pb2.HealthCheckRequest(
                service="deepfilter"
            )
        )

        try:

            response = await stub.HealthCheck(
                request
            )

        except grpc.aio.AioRpcError as exc:

            logger.error(
                "DeepFilter health check failed "
                "code=%s details=%s",
                exc.code(),
                exc.details(),
            )

            raise

        return response

    # =========================================================
    # Close
    # =========================================================

    async def close(self) -> None:
        """
        Close the gRPC channel.
        """

        if self.channel is not None:

            logger.info(
                "Closing DeepFilter gRPC connection"
            )

            await self.channel.close()

            self.channel = None
            self.stub = None


deepfilter_client = DeepFilterClient()
