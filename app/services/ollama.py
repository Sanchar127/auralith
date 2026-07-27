import logging

from ollama import Client
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.song import SongSpec

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are Auralith.

You are an AI music composer.

Your ONLY job is to generate JSON.

Do NOT explain anything.

Do NOT use markdown.

Do NOT wrap the JSON inside ```.

Follow the provided JSON schema EXACTLY.

Rules:

- title must be a string.
- genre must be a string.
- mood must be a string.
- tempo must be an integer.
- key must be a string.
- time_signature must be a string.

- sections MUST exist.

Each section MUST contain:

{
    "name":"Verse 1",
    "lyrics":[
        "line one",
        "line two"
    ],
    "chords":[
        "C",
        "G",
        "Am",
        "F"
    ]
}

- instruments must be a flat array of strings.

GOOD:

"instruments":[
    "Piano",
    "Drums",
    "Bass"
]

BAD:

"instruments":[
    ["Piano","Bass"],
    ["Drums"]
]

Never return nested arrays.

Return JSON only.
"""


class OllamaService:
    def __init__(self):
        self.client = Client(
            host=settings.OLLAMA_BASE_URL,
        )

    async def chat(self, prompt: str) -> SongSpec:
        last_error = None

        for attempt in range(3):
            try:
                response = self.client.chat(
                    model=settings.OLLAMA_MODEL,
                    format=SongSpec.model_json_schema(),
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

                return SongSpec.model_validate_json(content)

            except ValidationError as e:
                last_error = e

                logger.warning(
                    "Schema validation failed. Retrying (%s/3)...",
                    attempt + 1,
                )

            except Exception as e:
                logger.exception("Ollama request failed.")
                raise RuntimeError(str(e))

        raise RuntimeError(
            f"""
Ollama failed to generate a valid SongSpec after 3 attempts.

Validation Error:

{last_error}
"""
        )


ollama_service = OllamaService()