from __future__ import annotations

from app.core.logger import logger


SYSTEM_PROMPT = """
You are Auralith, an AI-powered audio processing platform.

Your primary capabilities are:

- Speech enhancement
- Music enhancement and mastering
- Audio encoding and transcoding
- Noise reduction
- Audio quality analysis
- Audio engineering assistance

When users ask to process audio:
- Explain the processing pipeline.
- Guide them to upload an audio file if required.
- Never pretend an audio file has been processed.

When users ask technical questions:
- Give accurate, concise answers.
- Use retrieved knowledge whenever available.

If the information is unavailable, say so rather than making up an answer.
"""
class PromptBuilder:
    """
    Builds the final prompt
    sent to Ollama.
    """

    def build(
        self,
        message: str,
        context: str,
        history: list[dict],
    ) -> list[dict]:

        logger.info(
            "Building prompt."
        )

        messages = [

            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }

        ]

        # -----------------------------
        # Conversation history
        # -----------------------------

        if history:

            messages.extend(history)

        # -----------------------------
        # Retrieved documents
        # -----------------------------

        if context:

            messages.append(

                {
                    "role": "system",
                    "content": f"""
Relevant Knowledge:

{context}
""",
                }

            )

        # -----------------------------
        # Current user message
        # -----------------------------

        messages.append(

            {
                "role": "user",
                "content": message,
            }

        )

        logger.debug(
            "Prompt contains %s messages.",
            len(messages),
        )

        return messages


prompt_builder = PromptBuilder()