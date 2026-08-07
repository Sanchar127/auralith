from pathlib import Path
import shutil


class DeepFilterNetService:

    def enhance(
        self,
        input_file: str,
        output_file: str,
    ) -> str:
        """
        Placeholder implementation.

        Later this will call DeepFilterNet.
        """

        Path(output_file).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy(
            input_file,
            output_file,
        )

        return output_file