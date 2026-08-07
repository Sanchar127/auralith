from pathlib import Path
import tempfile

from fastapi import FastAPI
from fastapi import File
from fastapi import UploadFile

from enhance import DeepFilterNetService
from health import router as health_router

app = FastAPI(
    title="DeepFilterNet Service",
    version="1.0.0",
)

app.include_router(health_router)

service = DeepFilterNetService()


@app.post("/enhance")
async def enhance_audio(
    file: UploadFile = File(...),
):
    suffix = Path(file.filename).suffix

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_input:

        temp_input.write(await file.read())

        input_path = temp_input.name

    output_path = f"output/{Path(file.filename).stem}_enhanced.wav"

    service.enhance(
        input_path,
        output_path,
    )

    return {
        "success": True,
        "filename": output_path,
        "message": "Audio enhanced successfully."
    }