from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from uuid import uuid4


class YueService:
    """
    Executes Yue inference.
    """

    def __init__(self) -> None:

        self.workspace = Path("/workspace")
        self.inference = self.workspace / "inference"
        self.jobs = self.workspace / "jobs"

        self.jobs.mkdir(
            parents=True,
            exist_ok=True,
        )

    def generate(
        self,
        genre: str,
        lyrics: str,
    ) -> dict[str, str]:

        job_id = uuid4().hex

        job_dir = self.jobs / job_id
        output_dir = job_dir / "output"

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        genre_file = job_dir / "genre.txt"
        lyrics_file = job_dir / "lyrics.txt"

        genre_file.write_text(
            genre,
            encoding="utf-8",
        )

        lyrics_file.write_text(
            lyrics,
            encoding="utf-8",
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

        result = subprocess.run(
            command,
            cwd=self.inference,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:

            raise RuntimeError(
                f"""
Yue generation failed.

STDOUT

{result.stdout}

STDERR

{result.stderr}
"""
            )

        wavs = list(output_dir.rglob("*.wav"))

        if not wavs:

            raise RuntimeError(
                "No wav files were generated."
            )

        files = {}

        for wav in wavs:

            name = wav.stem.lower()

            if "mix" in name:
                files["mix"] = str(wav)

            elif "vocal" in name:
                files["vocals"] = str(wav)

            elif "inst" in name:
                files["instrumental"] = str(wav)

        if "mix" not in files:

            files["mix"] = str(wavs[0])

        files["job_id"] = job_id

        return files


yue_service = YueService()