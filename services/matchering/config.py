from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"


INPUT_DIR.mkdir(
    exist_ok=True
)

OUTPUT_DIR.mkdir(
    exist_ok=True
)


TARGET_LUFS = -14.0


SUPPORTED_FORMATS = [
    ".mp3",
    ".wav",
    ".flac",
    ".m4a"
]