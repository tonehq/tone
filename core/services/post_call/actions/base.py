from abc import ABC, abstractmethod

from core.models.call import Call


class PostCallAction(ABC):
    """Contract for a single post-call side-effect.

    Each action is responsible for enqueuing its own background job. The
    handler treats actions as independent — one failing action must not
    stop the others.
    """

    name: str

    @abstractmethod
    def enqueue(self, call: Call) -> None:
        """Fire-and-forget: schedule the action's background work for ``call``."""
        raise NotImplementedError
