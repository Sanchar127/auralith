from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class DeepFilterNetService:
    """
    Service responsible for running DeepFilterNet inference.
    """

    def __init__(self) -> None:
        self.command = "deepFilter"

    def enhance(
        self,
        input_path: str,
        output_path: str,
    ) -> None:
        input_file = Path(input_path)
        output_file = Path(output_path)

        # -----------------------------------------------------
        # Validate input
        # -----------------------------------------------------

        if not input_file.exists():
            raise FileNotFoundError(
                f"Input audio does not exist: {input_file}"
            )

        if not input_file.is_file():
            raise ValueError(
                f"Input audio path is not a file: {input_file}"
            )

        if input_file.stat().st_size == 0:
            raise ValueError(
                f"Input audio is empty: {input_file}"
            )

        # -----------------------------------------------------
        # Prepare output directory
        # -----------------------------------------------------

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_output_dir = (
            output_file.parent / "deepfilter_output"
        )

        temp_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # -----------------------------------------------------
        # Run DeepFilterNet
        # -----------------------------------------------------

        command = [
            self.command,
            "-m",
            "DeepFilterNet3",
            "-o",
            str(temp_output_dir),
            str(input_file),
        ]

        logger.info(
            "Running DeepFilterNet: %s",
            " ".join(command),
        )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

        except FileNotFoundError as exc:
            raise RuntimeError(
                "DeepFilterNet executable was not found."
            ) from exc

        # -----------------------------------------------------
        # Log output
        # -----------------------------------------------------

        if result.stdout:
            logger.info(
                "DeepFilterNet stdout:\n%s",
                result.stdout,
            )

        if result.stderr:
            logger.warning(
                "DeepFilterNet stderr:\n%s",
                result.stderr,
            )

        # -----------------------------------------------------
        # Check result
        # -----------------------------------------------------

        if result.returncode != 0:
            raise RuntimeError(
                "DeepFilterNet failed "
                f"(exit code={result.returncode}): "
                f"{result.stderr.strip()}"
            )

        # -----------------------------------------------------
        # Find generated audio
        # -----------------------------------------------------

        audio_files = [
            path
            for path in temp_output_dir.iterdir()
            if path.is_file()
            and path.suffix.lower()
            in {
                ".wav",
                ".flac",
                ".ogg",
                ".mp3",
            }
        ]

        if not audio_files:
            raise RuntimeError(
                "DeepFilterNet completed but "
                "no output audio file was produced."
            )

        generated_file = audio_files[0]

        logger.info(
            "DeepFilterNet produced: %s",
            generated_file,
        )

        # -----------------------------------------------------
        # Move generated file to requested output
        # -----------------------------------------------------

        generated_file.replace(output_file)

        # -----------------------------------------------------
        # Verify output
        # -----------------------------------------------------

        if not output_file.exists():
            raise RuntimeError(
                "DeepFilterNet output was not created."
            )

        if output_file.stat().st_size == 0:
            raise RuntimeError(
                "DeepFilterNet produced an empty output."
            )

        logger.info(
            "Audio enhancement completed "
            "output=%s size=%d",
            output_file,
            output_file.stat().st_size,
        )