from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from pathlib import Path
import shutil


from config import (
    INPUT_DIR,
    OUTPUT_DIR,
    SUPPORTED_FORMATS
)


from analyzer import analyze_audio

from master import master_audio



app = FastAPI(
    title="Auralith Mastering Service"
)



@app.get("/")
def root():

    return {
        "service":
        "mastering",

        "status":
        "running"
    }



@app.post("/master")
async def master(
    file: UploadFile = File(...)
):


    ext = Path(
        file.filename
    ).suffix.lower()


    if ext not in SUPPORTED_FORMATS:

        raise HTTPException(
            400,
            "Only audio files allowed"
        )


    input_path = (
        INPUT_DIR /
        file.filename
    )


    with open(
        input_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )



    analysis = analyze_audio(
        str(input_path)
    )



    output_path = (
        OUTPUT_DIR /
        f"mastered_{file.filename}.wav"
    )


    master_audio(
        str(input_path),
        str(output_path)
    )



    return {

        "filename":
        file.filename,

        "output":
        str(output_path),

        "analysis":
        analysis,

        "message":
        "Mastering completed"

    }



@app.get("/health")
def health():

    return {
        "status":
        "healthy"
    }