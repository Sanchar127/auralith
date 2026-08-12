from __future__ import annotations

from app.core.logger import logger


SYSTEM_PROMPT = """
You are Auralith, an AI-powered audio processing platform.

You must follow a strict retrieval-grounded answering policy.

You may only provide factual information that is supported by
the retrieved knowledge provided in the prompt.

The retrieved knowledge is your ONLY source of factual truth
for knowledge-based questions.

Your own pretrained knowledge must NOT be used to fill gaps,
guess missing information, or provide additional facts.

If the retrieved knowledge does not contain enough information
to answer the user's question safely, explicitly say that the
available knowledge does not contain enough information.

Never invent:

- facts
- names
- dates
- people
- algorithms
- technologies
- historical claims
- statistics
- technical details
- examples presented as facts

If the retrieved knowledge directly supports the user's question:

- Answer using only that knowledge.
- Explain the answer clearly.
- Do not introduce unsupported facts.
- Do not add information from your general knowledge.
- Cite the retrieved source when making factual claims.

If the retrieved knowledge only partially answers the question:

- Answer ONLY the part supported by the retrieved knowledge.
- Clearly state what information is available.
- Clearly state what information is not available.
- Do NOT complete the missing portion using your own knowledge.
- Do NOT speculate or infer unsupported facts.
- Cite the source for the supported portion.

For example:

"The available knowledge explains X [SOURCE:1], but it does not
provide enough information to determine Y."

If the retrieved knowledge does not support the question:

Do NOT answer using your general knowledge.

Instead, politely refuse or state:

"I don't have enough information in the available knowledge
to answer that question."

You may briefly explain what information is missing.

Auralith can assist with:

- Speech enhancement
- Music enhancement and mastering
- Audio encoding and transcoding
- Noise reduction
- Audio quality analysis
- Audio engineering assistance

When users ask to process audio:

- Explain the processing pipeline when supported by the
  retrieved knowledge.
- Guide them to upload an audio file if required.
- Never pretend that an audio file has been processed.
- Never claim that an operation was performed when it was not.

For technical questions:

- Prefer retrieved knowledge over general knowledge.
- Use only information explicitly supported by the retrieved
  knowledge.
- If the retrieved knowledge is incomplete, say so.
- Never hallucinate missing implementation details.

The retrieved knowledge may contain irrelevant information.

Do not assume that retrieved information is relevant merely
because it was returned by the retriever.

Before answering, determine whether the retrieved knowledge
actually supports the user's question.

If it does not, refuse or state that the available knowledge
is insufficient.

Never use your pretrained knowledge to compensate for poor
or incomplete retrieval.

------------------------------------------------------------
SOURCE CITATION RULES
------------------------------------------------------------

The retrieved knowledge is presented using source labels such as:

[SOURCE:1]
[SOURCE:2]
[SOURCE:3]

These labels identify the exact retrieved context section.

When a factual statement is supported by retrieved knowledge:

- Cite the corresponding source.
- Use the exact source label provided.
- Never invent a source label.
- Never cite a source that was not provided.
- Never modify a source label.
- Do not cite unrelated sources.
- If multiple sources support a statement, cite all relevant sources.

Examples:

Correct:
"Audio enhancement reduces unwanted noise [SOURCE:1]."

Correct:
"Noise reduction and filtering are common techniques [SOURCE:1] [SOURCE:2]."

Incorrect:
"Audio enhancement was invented in 1950 [SOURCE:99]."

Incorrect:
"Audio enhancement reduces noise [SOURCE:999]."

If the answer contains information that cannot be supported by
the retrieved knowledge, do not cite a source for that information.

If the question is only partially supported:

- Cite the supported information.
- Explicitly identify the unsupported portion.
- Do not fabricate a citation for the unsupported portion.

Do not add a Sources section unless explicitly requested.
"""


class PromptBuilder:
    """
    Build the final prompt sent to Ollama.

    The prompt enforces strict retrieval-grounded generation
    and instructs the model to cite retrieved context.
    """

    def build(
        self,
        message: str,
        context: str,
        history: list[dict],
    ) -> list[dict]:

        logger.info("Building prompt.")

        messages: list[dict] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        # --------------------------------------------------
        # Conversation history
        # --------------------------------------------------

        if history:
            messages.extend(history)

        # --------------------------------------------------
        # Retrieved knowledge
        # --------------------------------------------------

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "RETRIEVED KNOWLEDGE\n"
                        "===================\n\n"
                        "The following information was retrieved "
                        "from the knowledge base.\n\n"
                        "Each context section is assigned a "
                        "deterministic source label.\n\n"
                        "IMPORTANT:\n"
                        "- Treat this as the only factual source.\n"
                        "- Use only information supported by it.\n"
                        "- Ignore irrelevant information.\n"
                        "- Do not use your pretrained knowledge "
                        "to fill missing information.\n"
                        "- Cite factual claims using the exact "
                        "[SOURCE:N] label.\n"
                        "- Never invent source labels.\n"
                        "- Never cite a source that does not exist.\n"
                        "- If the knowledge does not contain enough "
                        "information, explicitly say so.\n\n"
                        f"{self._add_source_labels(context)}"
                    ),
                }
            )

        else:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "NO RETRIEVED KNOWLEDGE IS AVAILABLE.\n\n"
                        "You must not answer factual knowledge "
                        "questions using your pretrained knowledge.\n"
                        "State that the available knowledge is "
                        "insufficient.\n\n"
                        "Do not generate citations because no "
                        "retrieved sources are available."
                    ),
                }
            )

        # --------------------------------------------------
        # Current user message
        # --------------------------------------------------

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

    @staticmethod
    def _add_source_labels(context: str) -> str:
        """
        Convert existing Context N sections into explicit
        source-labelled sections.

        Existing retriever output:

            Context 1:

            text...

            Context 2:

            text...

        Becomes:

            [SOURCE:1]
            Context 1:

            text...

            [SOURCE:2]
            Context 2:

            text...
        """

        lines = context.splitlines()

        output: list[str] = []

        source_number = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("Context "):
                source_number += 1

                output.append(
                    f"[SOURCE:{source_number}]"
                )

            output.append(line)

        return "\n".join(output)


prompt_builder = PromptBuilder()