from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    metadata: dict[str, str | int]
    id: str
