from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class RetrievalTestCase:
    query: str
    relevant_chunk_ids: set[str]


def load_dataset(
    path: str | Path,
) -> list[RetrievalTestCase]:

    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return [
        RetrievalTestCase(
            query=item["query"],
            relevant_chunk_ids=set(
                item["relevant_chunk_ids"]
            ),
        )
        for item in data
    ]