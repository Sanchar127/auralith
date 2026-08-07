import tiktoken


class TokenCounter:

    def __init__(self):
        self.encoder = tiktoken.get_encoding(
            "cl100k_base"
        )


    def count(
        self,
        text: str,
    ) -> int:

        if not text:
            return 0

        return len(
            self.encoder.encode(text)
        )


token_counter = TokenCounter()