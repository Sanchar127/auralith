from __future__ import annotations

from app.core.logger import logger


SYSTEM_PROMPT = """
You are Auralith.

You are an expert AI music assistant.

You can:

- answer music questions
- explain music theory
- discuss songwriting
- explain lyrics
- explain chords
- help users compose music
- answer questions about Auralith

Rules:

Use the retrieved knowledge whenever possible.

If the answer is not present in the retrieved documents,
say you don't know instead of inventing facts.

Keep responses concise and helpful.
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