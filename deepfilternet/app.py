from __future__ import annotations

from pathlib import Path
import tempfile

from fastapi import FastAPI, File, UploadFile

from enhance import DeepFilterNetService
from health import router as health_router
from logger import logger


# =========================================================
# Configuration
# =========================================================

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8001

SERVICE_VERSION = "1.0.0"


# =========================================================
# DeepFilterNet service
# =========================================================

service = DeepFilterNetService()


# =========================================================
# FastAPI application
# =========================================================

app = FastAPI(
    title="Auralith DeepFilterNet Service",
    version=SERVICE_VERSION,
)

app.include_router(
    health_router,
)


# =========================================================
# Manual HTTP testing endpoint
# =========================================================

@app.post("/enhance")
async def enhance_audio(
    file: UploadFile = File(...),
):
    """
    Manually enhance an uploaded audio file.

    This endpoint is intended for local testing.

    Production audio processing should happen through:

        Auralith
            ↓
        RabbitMQ
            ↓
        Celery
            ↓
        DeepFilterNet worker
    """

    suffix = (
        Path(file.filename).suffix
        if file.filename
        else ".wav"
    )

    input_path: str | None = None

    try:

        # -----------------------------------------------------
        # Create temporary input file
        # -----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_input:

            input_path = temp_input.name

            while True:

                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                temp_input.write(chunk)

        # -----------------------------------------------------
        # Create output path
        # -----------------------------------------------------

        output_dir = Path("output")

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            Path(
                file.filename or "audio"
            ).stem
        )

        output_path = (
            output_dir
            / f"{filename}_enhanced.wav"
        )

        # -----------------------------------------------------
        # Run DeepFilterNet
        # -----------------------------------------------------

        logger.info(
            "Starting manual audio enhancement. "
            "filename=%s",
            file.filename,
        )

        service.enhance(
            input_path,
            str(output_path),
        )

        logger.info(
            "Manual audio enhancement completed. "
            "output=%s",
            output_path,
        )

        return {
            "success": True,
            "filename": str(output_path),
            "message": (
                "Audio enhanced successfully."
            ),
        }

    except Exception as exc:

        logger.exception(
            "Manual audio enhancement failed."
        )

        raise

    finally:

        # -----------------------------------------------------
        # Cleanup temporary input
        # -----------------------------------------------------

        if input_path:

            Path(input_path).unlink(
                missing_ok=True,
            )