import logging

from ollama import Client
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.audio import AudioGenerationRequest

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are Auralith.

You are an AI assistant for audio processing.

Your ONLY task is to generate valid JSON.

Do NOT explain anything.
Do NOT use markdown.
Do NOT wrap the JSON inside triple backticks.

Follow the provided JSON schema exactly.

The JSON must describe the requested audio processing task.

Supported operations:

- enhance
- master
- encode
- analyze

Rules:

- operation must be one of the supported operations.
- output_format must be a valid audio format when applicable (wav, mp3, flac, aac, ogg).
- Preserve the user's intent.
- Do not invent information that was not provided.
- If an output format is not requested, return null.

Return ONLY valid JSON.
"""

class OllamaService:
    """
    Generates structured audio generation requests
    using Ollama.
    """

    def __init__(self):
        self.client = Client(
            host=settings.OLLAMA_BASE_URL,
        )

    async def chat(
        self,
        prompt: str,
    ) -> AudioGenerationRequest:

        last_error = None

        for attempt in range(3):

            try:

                response = self.client.chat(
                    model=settings.OLLAMA_MODEL,
                    format=AudioGenerationRequest.model_json_schema(),
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                )

                content = response["message"]["content"]

                logger.info("=" * 80)
                logger.info("OLLAMA RAW RESPONSE")
                logger.info(content)
                logger.info("=" * 80)

                return AudioGenerationRequest.model_validate_json(
                    content
                )

            except ValidationError as exc:

                last_error = exc

                logger.warning(
                    "Schema validation failed (%s/3). Retrying...",
                    attempt + 1,
                )

            except Exception as exc:

                logger.exception(
                    "Ollama request failed."
                )

                raise RuntimeError(
                    f"Failed to communicate with Ollama: {exc}"
                ) from exc

        raise RuntimeError(
            f"""
Failed to generate a valid AudioGenerationRequest after 3 attempts.

Validation error:

{last_error}
"""
        )


ollama_service = OllamaService()