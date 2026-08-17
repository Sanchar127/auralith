from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)


class DeepFilterNetError(RuntimeError):
    """Base exception for DeepFilterNet failures."""


class DeepFilterNetExecutableError(DeepFilterNetError):
    """Raised when the DeepFilterNet executable cannot be started."""


class DeepFilterNetTimeoutError(DeepFilterNetError):
    """Raised when DeepFilterNet exceeds the configured timeout."""


class DeepFilterNetInferenceError(DeepFilterNetError):
    """Raised when DeepFilterNet exits unsuccessfully."""


class DeepFilterNetOutputError(DeepFilterNetError):
    """Raised when DeepFilterNet does not produce valid output."""


class DeepFilterNetService:
    """
    Production-grade DeepFilterNet inference service.

    Responsibilities
    ----------------
    - Validate local input audio.
    - Execute DeepFilterNet safely.
    - Enforce an inference timeout.
    - Capture and bound subprocess logs.
    - Validate generated output.
    - Atomically move the generated file to the requested path.

    This class intentionally does NOT:
    - communicate with MinIO
    - communicate with RabbitMQ
    - update database records
    - manage Celery
    - manage HTTP requests

    Those responsibilities belong to the surrounding application layers.
    """

    DEFAULT_COMMAND: Final[str] = "deepFilter"
    DEFAULT_MODEL: Final[str] = "DeepFilterNet3"
    DEFAULT_TIMEOUT_SECONDS: Final[int] = 15 * 60
    DEFAULT_MAX_LOG_BYTES: Final[int] = 16 * 1024

    SUPPORTED_OUTPUT_EXTENSIONS: Final[frozenset[str]] = frozenset(
        {
            ".wav",
            ".flac",
            ".ogg",
            ".mp3",
        }
    )

    def __init__(
        self,
        *,
        command: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_log_bytes: int | None = None,
    ) -> None:
        """
        Initialize the DeepFilterNet service.

        Environment variables:

            DEEPFILTER_COMMAND
            DEEPFILTER_MODEL
            DEEPFILTER_TIMEOUT_SECONDS
            DEEPFILTER_MAX_LOG_BYTES
        """

        self.command = (
            command
            or os.getenv(
                "DEEPFILTER_COMMAND",
                self.DEFAULT_COMMAND,
            )
        )

        self.model = (
            model
            or os.getenv(
                "DEEPFILTER_MODEL",
                self.DEFAULT_MODEL,
            )
        )

        self.timeout_seconds = self._positive_int(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv(
                "DEEPFILTER_TIMEOUT_SECONDS"
            ),
            default=self.DEFAULT_TIMEOUT_SECONDS,
        )

        self.max_log_bytes = self._positive_int(
            max_log_bytes
            if max_log_bytes is not None
            else os.getenv(
                "DEEPFILTER_MAX_LOG_BYTES"
            ),
            default=self.DEFAULT_MAX_LOG_BYTES,
        )

        logger.info(
            "DeepFilterNet service initialized "
            "command=%s model=%s timeout_seconds=%s",
            self.command,
            self.model,
            self.timeout_seconds,
        )

    # =========================================================
    # PUBLIC API
    # =========================================================

    def enhance(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        Enhance an audio file using DeepFilterNet.

        Parameters
        ----------
        input_path:
            Path to the locally downloaded input audio.

        output_path:
            Final path where the enhanced audio should be written.

        Returns
        -------
        Path
            Path to the successfully generated output.

        Raises
        ------
        FileNotFoundError
            If the input file does not exist.

        DeepFilterNetExecutableError
            If DeepFilterNet cannot be started.

        DeepFilterNetTimeoutError
            If inference exceeds the configured timeout.

        DeepFilterNetInferenceError
            If DeepFilterNet exits with a non-zero status.

        DeepFilterNetOutputError
            If no valid output is produced.
        """

        input_file = Path(input_path)
        output_file = Path(output_path)

        self._validate_input(input_file)
        self._prepare_output_path(output_file)

        logger.info(
            "Starting DeepFilterNet inference "
            "input=%s output=%s model=%s",
            input_file,
            output_file,
            self.model,
        )

        with tempfile.TemporaryDirectory(
            prefix="deepfilternet-",
            dir=output_file.parent,
        ) as temp_dir:

            inference_dir = Path(temp_dir)

            self._run_inference(
                input_file=input_file,
                output_dir=inference_dir,
            )

            generated_file = self._find_output(
                output_dir=inference_dir,
                input_file=input_file,
            )

            self._validate_output(generated_file)

            self._move_output(
                source=generated_file,
                destination=output_file,
            )

        self._validate_output(output_file)

        logger.info(
            "DeepFilterNet inference completed "
            "input=%s output=%s size=%d",
            input_file,
            output_file,
            output_file.stat().st_size,
        )

        return output_file

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _validate_input(
        input_file: Path,
    ) -> None:
        """Validate the local input audio file."""

        if not input_file.exists():
            raise FileNotFoundError(
                f"Input audio does not exist: {input_file}"
            )

        if not input_file.is_file():
            raise ValueError(
                f"Input audio path is not a file: {input_file}"
            )

        try:
            size = input_file.stat().st_size
        except OSError as exc:
            raise DeepFilterNetError(
                f"Unable to inspect input audio: {input_file}"
            ) from exc

        if size <= 0:
            raise ValueError(
                f"Input audio is empty: {input_file}"
            )

    @staticmethod
    def _prepare_output_path(
        output_file: Path,
    ) -> None:
        """Prepare the destination directory."""

        if output_file.suffix.lower() not in (
            DeepFilterNetService.SUPPORTED_OUTPUT_EXTENSIONS
        ):
            raise ValueError(
                "Unsupported output format: "
                f"{output_file.suffix}"
            )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Never allow a previous result to be mistaken for
        # the result of the current inference.
        if output_file.exists():
            output_file.unlink()

    @staticmethod
    def _validate_output(
        output_file: Path,
    ) -> None:
        """Validate a generated audio file."""

        if not output_file.exists():
            raise DeepFilterNetOutputError(
                f"DeepFilterNet output does not exist: "
                f"{output_file}"
            )

        if not output_file.is_file():
            raise DeepFilterNetOutputError(
                f"DeepFilterNet output is not a file: "
                f"{output_file}"
            )

        try:
            size = output_file.stat().st_size
        except OSError as exc:
            raise DeepFilterNetOutputError(
                f"Unable to inspect DeepFilterNet output: "
                f"{output_file}"
            ) from exc

        if size <= 0:
            raise DeepFilterNetOutputError(
                f"DeepFilterNet produced an empty file: "
                f"{output_file}"
            )

    # =========================================================
    # INFERENCE
    # =========================================================

    def _run_inference(
        self,
        *,
        input_file: Path,
        output_dir: Path,
    ) -> None:
        """Execute DeepFilterNet without invoking a shell."""

        command = [
            self.command,
            "-m",
            self.model,
            "-o",
            str(output_dir),
            str(input_file),
        ]

        logger.info(
            "Executing DeepFilterNet "
            "model=%s input=%s",
            self.model,
            input_file,
        )

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=self.timeout_seconds,
                shell=False,
            )

        except FileNotFoundError as exc:
            logger.exception(
                "DeepFilterNet executable not found "
                "command=%s",
                self.command,
            )

            raise DeepFilterNetExecutableError(
                f"DeepFilterNet executable not found: "
                f"{self.command}"
            ) from exc

        except subprocess.TimeoutExpired as exc:
            logger.error(
                "DeepFilterNet inference timed out "
                "timeout_seconds=%s input=%s",
                self.timeout_seconds,
                input_file,
            )

            raise DeepFilterNetTimeoutError(
                "DeepFilterNet inference exceeded "
                f"{self.timeout_seconds} seconds"
            ) from exc

        except OSError as exc:
            logger.exception(
                "Failed to execute DeepFilterNet "
                "command=%s",
                self.command,
            )

            raise DeepFilterNetExecutableError(
                "Unable to execute DeepFilterNet"
            ) from exc

        stdout = self._truncate_log(result.stdout)
        stderr = self._truncate_log(result.stderr)

        if stdout:
            logger.debug(
                "DeepFilterNet stdout:\n%s",
                stdout,
            )

        if stderr:
            logger.debug(
                "DeepFilterNet stderr:\n%s",
                stderr,
            )

        if result.returncode != 0:

            logger.error(
                "DeepFilterNet failed "
                "returncode=%s input=%s stderr=%s",
                result.returncode,
                input_file,
                stderr,
            )

            raise DeepFilterNetInferenceError(
                "DeepFilterNet inference failed "
                f"(exit code={result.returncode})"
            )

        logger.info(
            "DeepFilterNet process completed "
            "returncode=%s",
            result.returncode,
        )

    # =========================================================
    # OUTPUT DISCOVERY
    # =========================================================

    def _find_output(
        self,
        *,
        output_dir: Path,
        input_file: Path,
    ) -> Path:
        """
        Locate the audio file generated by DeepFilterNet.

        Only files created inside the isolated inference directory
        are considered.
        """

        if not output_dir.exists():
            raise DeepFilterNetOutputError(
                "DeepFilterNet output directory was not created"
            )

        candidates = sorted(
            (
                path
                for path in output_dir.rglob("*")
                if path.is_file()
                and path.suffix.lower()
                in self.SUPPORTED_OUTPUT_EXTENSIONS
            ),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )

        if not candidates:
            raise DeepFilterNetOutputError(
                "DeepFilterNet completed successfully "
                "but produced no audio output"
            )

        if len(candidates) > 1:
            logger.warning(
                "DeepFilterNet produced multiple output files "
                "input=%s candidates=%s",
                input_file,
                [str(path) for path in candidates],
            )

        generated_file = candidates[0]

        logger.info(
            "DeepFilterNet output discovered "
            "input=%s output=%s",
            input_file,
            generated_file,
        )

        return generated_file

    # =========================================================
    # FILE HANDLING
    # =========================================================

    @staticmethod
    def _move_output(
        *,
        source: Path,
        destination: Path,
    ) -> None:
        """
        Move generated output into its final location.

        shutil.move is used instead of rename because the
        implementation remains safe if temporary/output
        directories are mounted differently.
        """

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            shutil.move(
                str(source),
                str(destination),
            )
        except OSError as exc:
            raise DeepFilterNetOutputError(
                "Failed to move DeepFilterNet output "
                f"from {source} to {destination}"
            ) from exc

    # =========================================================
    # LOGGING / CONFIG
    # =========================================================

    def _truncate_log(
        self,
        value: str,
    ) -> str:
        """Prevent unbounded subprocess output from entering logs."""

        if not value:
            return ""

        if len(value) <= self.max_log_bytes:
            return value

        return (
            value[: self.max_log_bytes]
            + "\n...[output truncated]..."
        )

    @staticmethod
    def _positive_int(
        value: int | str | None,
        *,
        default: int,
    ) -> int:
        """Parse a positive integer configuration value."""

        if value is None:
            return default

        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Expected a positive integer, got {value!r}"
            ) from exc

        if parsed <= 0:
            raise ValueError(
                f"Expected a positive integer, got {parsed}"
            )

        return parsed


deepfilter_service = DeepFilterNetService()