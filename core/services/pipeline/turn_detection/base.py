from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, List, Optional


@dataclass(frozen=True)
class TurnDetectionContext:
    llm_context: Any = None
    language: Optional[str] = None


class TurnDetector(ABC):
    slug: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str]
    schema: ClassVar[List[dict]] = []

    def __init__(self, settings: dict):
        self.settings = settings

    @classmethod
    def available(cls) -> bool:
        return True

    @property
    def fallback_timeout_secs(self) -> Optional[float]:
        return None

    @abstractmethod
    def build(self, context: TurnDetectionContext) -> list:
        ...

    def describe(self) -> dict:
        return {"provider": self.slug, **self.settings}
