import librosa
import numpy as np


def analyze_audio(path: str):

    audio, sr = librosa.load(
        path,
        sr=None,
        mono=False
    )


    if audio.ndim > 1:
        mono = librosa.to_mono(audio)
    else:
        mono = audio


    tempo, _ = librosa.beat.beat_track(
        y=mono,
        sr=sr
    )


    spectral = librosa.feature.spectral_centroid(
        y=mono,
        sr=sr
    )


    brightness = float(
        np.mean(spectral)
    )


    rms = float(
        np.mean(
            librosa.feature.rms(
                y=mono
            )
        )
    )


    return {

        "sample_rate": sr,

        "bpm": float(
            tempo
        ),

        "brightness": brightness,

        "energy": rms

    }