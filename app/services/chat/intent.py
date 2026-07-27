from ollama import AsyncClient

from app.core.config import settings
from app.core.logger import logger


SYSTEM_PROMPT = """
You are an intent classifier for Auralith.

Classify the user's request into exactly ONE of these labels:

song
chat

Return ONLY the label.

Examples:

User:
Write me a sad piano ballad.

song

User:
Generate an EDM track with female vocals.

song

User:
Compose a rock song about freedom.

song

User:
What instruments are used in jazz?

chat

User:
Explain chord progression.

chat

User:
What is the difference between major and minor scales?

chat

User:
Hello

chat

User:
How are you?

chat

Rules:

- If the user wants music, lyrics, a song, melody, chords, composition, or audio generation -> song
- Otherwise -> chat

Return only:

song

or

chat
"""


class IntentClassifier:
    """
    Determines whether a request is for
    song generation or normal conversation.
    """

    def __init__(self):

        self.client = AsyncClient(
            host=settings.OLLAMA_BASE_URL,
        )

        self.model = settings.OLLAMA_MODEL

    async def classify(
        self,
        message: str,
    ) -> str:

        logger.info(
            "Classifying user intent."
        )

        try:

            response = await self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": message,
                    },
                ],
            )

            intent = (
                response["message"]["content"]
                .strip()
                .lower()
            )

            logger.info(
                "Detected intent=%s",
                intent,
            )

            if intent not in {
                "song",
                "chat",
            }:
                logger.warning(
                    "Unknown intent '%s'. Falling back to chat.",
                    intent,
                )
                return "chat"

            return intent

        except Exception:

            logger.exception(
                "Intent classification failed."
            )

            return "chat"


intent_classifier = IntentClassifier()