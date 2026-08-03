from pydantic import BaseModel, Field


class Note(BaseModel):
    pitch: str = Field(..., examples=["C4"])
    duration: float = Field(..., examples=[1.0])
    velocity: int = Field(90, ge=1, le=127)


class MelodyBar(BaseModel):
    notes: list[Note]


class Section(BaseModel):
    name: str

    lyrics: list[str]

    chords: list[str]

    melody: list[MelodyBar]


class SongSpec(BaseModel):
    title: str

    genre: str

    mood: str

    tempo: int

    key: str

    time_signature: str

    instruments: list[str]

    sections: list[Section]