from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logger import logger


class YuEClient:

    def __init__(self) -> None:
        self.base_url = settings.YUE_BASE_URL.rstrip("/")

    async def generate_song(
        self,
        *,
        title: str,
        genre: str,
        lyrics: str,
    ) -> str:
        """
        Generate a song using the YuE service.

        Returns:
            Absolute path of generated MP3 inside the YuE container.
        """

        logger.info(
            "Sending song generation request to YuE..."
        )

        payload = {
            "title": title,
            "genre": genre,
            "lyrics": lyrics,
        }

        try:

            async with httpx.AsyncClient(
                timeout=None,
            ) as client:

                response = await client.post(
                    f"{self.base_url}/generate",
                    json=payload,
                )

            response.raise_for_status()

            data = response.json()

            logger.info(
                "YuE generation completed."
            )

            if not data.get("success"):

                raise RuntimeError(
                    data.get(
                        "message",
                        "YuE generation failed.",
                    )
                )

            mp3 = data["mp3"]

            if not Path(mp3).suffix == ".mp3":

                raise RuntimeError(
                    "YuE did not return an MP3 file."
                )

            logger.info(
                "Generated MP3: %s",
                mp3,
            )

            return mp3

        except Exception:

            logger.exception(
                "Failed to generate song with YuE."
            )

            raise


yue_client = YuEClient()