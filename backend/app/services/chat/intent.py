from ollama import AsyncClient

from app.core.config import settings
from app.core.logger import logger


SYSTEM_PROMPT = """
You are an intent classifier for Auralith.

Auralith is an AI-powered audio processing platform.

Classify the user's request into exactly ONE of the following labels:

chat
enhance
master
encode
analyze

Definitions:

chat
- General conversation
- Questions about Auralith
- Audio engineering questions
- Technical support
- Explanations

enhance
- Remove background noise
- Enhance speech clarity
- Improve vocal quality
- Audio restoration
- Speech enhancement

master
- Master a song
- Improve music loudness
- Audio mastering
- Loudness normalization
- Final mix processing

encode
- Convert audio formats
- Compress audio
- Change bitrate
- Change sample rate
- Transcode audio

analyze
- Detect BPM
- Detect musical key
- Analyze loudness
- Analyze audio quality
- Extract audio metadata

Rules:

- Return exactly ONE label.
- Do not explain your answer.
- Do not include punctuation.
- If uncertain, return "chat".

Examples:

User: Remove background noise from this recording.
enhance

User: Improve my voice recording.
enhance

User: Master this song.
master

User: Normalize loudness to -14 LUFS.
master

User: Convert WAV to MP3.
encode

User: Convert this audio to FLAC.
encode

User: What's the BPM of this song?
analyze

User: Analyze this audio file.
analyze

User: What is LUFS?
chat

User: Hello
chat

User: What can Auralith do?
chat
"""


VALID_INTENTS = {
    "chat",
    "enhance",
    "master",
    "encode",
    "analyze",
}


class IntentClassifier:
    """
    Determines the user's intent for routing
    requests within Auralith.
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

            if intent not in VALID_INTENTS:

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