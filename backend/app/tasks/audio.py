import asyncio
import json
from pathlib import Path
from uuid import uuid4

from app.core.logger import logger
from app.services.midi import midi_service
from app.services.ollama import ollama_service
from app.services.storage import storage_service
from app.workers.celery_app import celery


@celery.task(name="generate_song")
def generate_song(prompt: str):
    logger.info("Song generation task started.")

    song_id = uuid4().hex
    json_path = Path(f"storage/{song_id}.json")

    try:
        logger.info("Generating song from prompt...")
        song = asyncio.run(ollama_service.chat(prompt))

        logger.info("Song generated successfully. song_id=%s", song_id)

        logger.info("Generating MIDI/WAV/MP3 files...")
        # Generates MIDI and renders WAV/MP3 files locally
        files = midi_service.generate(
            song,
            f"storage/{song_id}.mid",
        )

        logger.info(
            "Audio files generated successfully. midi=%s wav=%s mp3=%s",
            files.get("midi"),
            files.get("wav"),
            files.get("mp3"),
        )

        # Save song metadata to local JSON
        json_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Saving SongSpec JSON to %s", json_path)

        song_data = (
            song.model_dump() if hasattr(song, "model_dump") else song.dict()
            if hasattr(song, "dict") else song
        )

        json_path.write_text(json.dumps(song_data, indent=2))

        # Upload files to MinIO storage
        logger.info("Uploading MP3 to MinIO...")
        mp3_key = storage_service.upload_file(
            files["mp3"],
            object_name=f"songs/{song_id}.mp3",
        )
        logger.info("MP3 uploaded successfully. object=%s", mp3_key)

        logger.info("Uploading MIDI to MinIO...")
        midi_key = storage_service.upload_file(
            files["midi"],
            object_name=f"songs/{song_id}.mid",
        )
        logger.info("MIDI uploaded successfully. object=%s", midi_key)

        logger.info("Uploading JSON metadata to MinIO...")
        json_key = storage_service.upload_file(
            str(json_path),
            object_name=f"songs/{song_id}.json",
        )
        logger.info("JSON uploaded successfully. object=%s", json_key)

        logger.info(
            "Song generation task completed successfully. song_id=%s",
            song_id,
        )

        return {
            "song_id": song_id,
            "mp3": mp3_key,
            "midi": midi_key,
            "json": json_key,
        }

    finally:
        # Cleanup temporary files created during processing
        for path_key in ["midi", "wav", "mp3"]:
            if 'files' in locals() and path_key in files:
                f_path = Path(files[path_key])
                if f_path.exists():
                    f_path.unlink(missing_ok=True)

        if json_path.exists():
            json_path.unlink(missing_ok=True)