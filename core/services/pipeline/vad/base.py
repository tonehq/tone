from abc import ABC, abstractmethod
from typing import ClassVar, List

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams


class VADProvider(ABC):
    slug: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str]
    schema: ClassVar[List[dict]] = []

    def __init__(self, settings: dict):
        self.settings = settings

    @classmethod
    def available(cls) -> bool:
        return True

    @abstractmethod
    def build(self, params: VADParams) -> VADAnalyzer:
        ...

    def describe(self) -> dict:
        return {"provider": self.slug, **self.settings}
