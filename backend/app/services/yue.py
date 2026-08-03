from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from app.core.logger import logger


class YueService:
    """
    Wrapper around the Yue inference pipeline.

    Responsible for:

    - Running infer.py
    - Returning generated audio paths
    """

    def __init__(self) -> None:

        self.workspace = Path("/workspace")

        self.inference_dir = (
            self.workspace / "inference"
        )

    def generate(
        self,
        genre_file: str | Path,
        lyrics_file: str | Path,
    ) -> dict[str, str]:

        genre_file = Path(genre_file)
        lyrics_file = Path(lyrics_file)

        output_dir = (
            self.inference_dir
            / "output"
            / uuid4().hex
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "Starting Yue generation."
        )

        command = [
            "python",
            "infer.py",
            "--genre_txt",
            str(genre_file),
            "--lyrics_txt",
            str(lyrics_file),
            "--output_dir",
            str(output_dir),
        ]

        logger.info(
            "Executing: %s",
            " ".join(command),
        )

        result = subprocess.run(
            command,
            cwd=self.inference_dir,
            capture_output=True,
            text=True,
        )

        logger.info(result.stdout)

        if result.returncode != 0:

            logger.error(result.stderr)

            shutil.rmtree(
                output_dir,
                ignore_errors=True,
            )

            raise RuntimeError(
                "Yue generation failed."
            )

        wav_files = sorted(
            output_dir.rglob("*.wav")
        )

        mp3_files = sorted(
            output_dir.rglob("*.mp3")
        )

        if not wav_files and not mp3_files:

            raise RuntimeError(
                "Yue completed but produced no audio."
            )

        files: dict[str, str] = {}

        for file in wav_files + mp3_files:

            name = file.stem.lower()

            if "mix" in name:
                files["mix"] = str(file)

            elif "vocal" in name:
                files["vocals"] = str(file)

            elif "inst" in name:
                files["instrumental"] = str(file)

            elif "accompaniment" in name:
                files["instrumental"] = str(file)

        if not files:

            files["audio"] = str(
                wav_files[0]
                if wav_files
                else mp3_files[0]
            )

        logger.info(
            "Yue generation finished."
        )

        return files


yue_service = YueService()