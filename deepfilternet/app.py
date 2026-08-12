
from __future__ import annotations

import asyncio
from concurrent import futures
from pathlib import Path
import tempfile
from logger import logger
import grpc
from fastapi import FastAPI, File, UploadFile

from enhance import DeepFilterNetService
from health import router as health_router

from generated import (
    deepfilter_pb2,
    deepfilter_pb2_grpc,
)


# =========================================================
# Configuration
# =========================================================

GRPC_HOST = "0.0.0.0"
GRPC_PORT = 50051

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8001

SERVICE_VERSION = "1.0.0"




# =========================================================
# DeepFilter service
# =========================================================

service = DeepFilterNetService()


# =========================================================
# FastAPI
# =========================================================

app = FastAPI(
    title="DeepFilterNet Service",
    version=SERVICE_VERSION,
)

app.include_router(
    health_router,
)


# =========================================================
# HTTP endpoint
#
# This endpoint is optional.
# It is useful for local/manual testing.
# Production backend communication uses gRPC.
# =========================================================

@app.post("/enhance")
async def enhance_audio(
    file: UploadFile = File(...),
):
    suffix = (
        Path(file.filename).suffix
        if file.filename
        else ".wav"
    )

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_input:

        temp_input.write(
            await file.read()
        )

        input_path = temp_input.name

    output_path = (
        f"output/"
        f"{Path(file.filename or 'audio').stem}"
        f"_enhanced.wav"
    )

    Path("output").mkdir(
        parents=True,
        exist_ok=True,
    )

    try:

        service.enhance(
            input_path,
            output_path,
        )

    finally:

        Path(input_path).unlink(
            missing_ok=True,
        )

    return {
        "success": True,
        "filename": output_path,
        "message": "Audio enhanced successfully.",
    }


# =========================================================
# gRPC Server
# =========================================================


class DeepFilterGrpcService(
    deepfilter_pb2_grpc.DeepFilterServiceServicer,
):
    """
    gRPC implementation of DeepFilterService.

    The backend sends MinIO object references.
    Audio bytes are NOT transferred through gRPC.
    """

    def __init__(self):
        self.jobs: dict[str, dict] = {}

    # -----------------------------------------------------
    # EnhanceAudio
    # -----------------------------------------------------

    async def EnhanceAudio(
        self,
        request,
        context,
    ):
        job_id = request.job_id

        logger.info(
            "EnhanceAudio request received "
            "job_id=%s input=%s output=%s",
            job_id,
            request.input_object_key,
            request.output_object_key,
        )

        self.jobs[job_id] = {
            "status": (
                deepfilter_pb2.PROCESSING
            ),
            "output_bucket": (
                request.output_bucket
            ),
            "output_object_key": (
                request.output_object_key
            ),
        }

        try:

            # =================================================
            # IMPORTANT
            #
            # This is where DeepFilterNet should:
            #
            # 1. Download input from MinIO
            # 2. Run DeepFilterNet
            # 3. Upload enhanced audio to MinIO
            # 4. Return the MinIO object reference
            #
            # Do NOT send audio bytes through gRPC.
            # =================================================

            logger.info(
                "Processing DeepFilter job "
                "job_id=%s",
                job_id,
            )

            # TODO:
            #
            # await minio.download_file(...)
            #
            # service.enhance(...)
            #
            # await minio.upload_file(...)

            self.jobs[job_id][
                "status"
            ] = deepfilter_pb2.COMPLETED

            return deepfilter_pb2.EnhanceAudioResponse(
                job_id=job_id,
                status=deepfilter_pb2.COMPLETED,
                output_bucket=(
                    request.output_bucket
                ),
                output_object_key=(
                    request.output_object_key
                ),
            )

        except Exception as exc:

            logger.exception(
                "DeepFilter processing failed "
                "job_id=%s",
                job_id,
            )

            error = deepfilter_pb2.Error(
                code="PROCESSING_ERROR",
                message=str(exc),
                retryable=True,
            )

            self.jobs[job_id] = {
                "status": (
                    deepfilter_pb2.FAILED
                ),
                "output_bucket": (
                    request.output_bucket
                ),
                "output_object_key": (
                    request.output_object_key
                ),
                "error": error,
            }

            return deepfilter_pb2.EnhanceAudioResponse(
                job_id=job_id,
                status=deepfilter_pb2.FAILED,
                output_bucket=(
                    request.output_bucket
                ),
                output_object_key=(
                    request.output_object_key
                ),
                error=error,
            )

    # -----------------------------------------------------
    # GetJobStatus
    # -----------------------------------------------------

    async def GetJobStatus(
        self,
        request,
        context,
    ):
        job_id = request.job_id

        job = self.jobs.get(job_id)

        if job is None:

            error = deepfilter_pb2.Error(
                code="JOB_NOT_FOUND",
                message="Job not found",
                retryable=False,
            )

            return deepfilter_pb2.GetJobStatusResponse(
                job_id=job_id,
                status=(
                    deepfilter_pb2.FAILED
                ),
                error=error,
            )

        response = deepfilter_pb2.GetJobStatusResponse(
            job_id=job_id,
            status=job["status"],
            output_bucket=job.get(
                "output_bucket",
                "",
            ),
            output_object_key=job.get(
                "output_object_key",
                "",
            ),
        )

        if "error" in job:
            response.error.CopyFrom(
                job["error"]
            )

        return response

    # -----------------------------------------------------
    # CancelJob
    # -----------------------------------------------------

    async def CancelJob(
        self,
        request,
        context,
    ):
        job_id = request.job_id

        job = self.jobs.get(job_id)

        if job is None:

            error = deepfilter_pb2.Error(
                code="JOB_NOT_FOUND",
                message="Job not found",
                retryable=False,
            )

            return deepfilter_pb2.CancelJobResponse(
                job_id=job_id,
                success=False,
                status=(
                    deepfilter_pb2.FAILED
                ),
                error=error,
            )

        job["status"] = (
            deepfilter_pb2.CANCELLED
        )

        logger.info(
            "DeepFilter job cancelled "
            "job_id=%s",
            job_id,
        )

        return deepfilter_pb2.CancelJobResponse(
            job_id=job_id,
            success=True,
            status=(
                deepfilter_pb2.CANCELLED
            ),
        )

    # -----------------------------------------------------
    # HealthCheck
    # -----------------------------------------------------

    async def HealthCheck(
        self,
        request,
        context,
    ):
        return deepfilter_pb2.HealthCheckResponse(
            status=deepfilter_pb2.HEALTHY,
            service=(
                request.service
                or "deepfilter"
            ),
            version=SERVICE_VERSION,
        )


# =========================================================
# Start gRPC server
# =========================================================


async def serve_grpc():
    server = grpc.aio.server()

    deepfilter_pb2_grpc.add_DeepFilterServiceServicer_to_server(
        DeepFilterGrpcService(),
        server,
    )

    address = (
        f"{GRPC_HOST}:{GRPC_PORT}"
    )

    server.add_insecure_port(address)

    logger.info(
        "DeepFilter gRPC server listening on %s",
        address,
    )

    await server.start()

    try:
        await server.wait_for_termination()

    finally:
        logger.info(
            "Stopping DeepFilter gRPC server"
        )

        await server.stop(
            grace=5,
        )


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        serve_grpc()
    )
