from uuid import uuid4

from app.services.midi import midi_service
from app.services.ollama import ollama_service
from app.services.storage import storage_service
from app.workers.celery_app import celery


@celery.task(name="generate_song")
def generate_song(prompt: str):

    # Generate the song structure
    song = ollama_service.chat_sync(prompt)

    # Unique ID for this song
    song_id = uuid4().hex

    # Generate MIDI, WAV, and MP3
    files = midi_service.generate(
        song,
        f"storage/{song_id}.mid",
    )

    # Upload MP3
    mp3_key = storage_service.upload_file(
        files["mp3"],
        object_name=f"songs/{song_id}.mp3",
    )

    # Optionally upload MIDI
    midi_key = storage_service.upload_file(
        files["midi"],
        object_name=f"songs/{song_id}.mid",
    )

    return {
        "id": song_id,
        "song": song.model_dump(),
        "mp3": mp3_key,
        "midi": midi_key,
    }