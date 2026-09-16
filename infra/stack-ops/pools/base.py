"""Strategy contract for the app node pool. Add a cloud: add one file + one line in __init__.py."""

import abc


class AppNodePool(abc.ABC):
    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg

    @abc.abstractmethod
    def create(self, opts):
        """Create the node pool on the existing cluster and return the Pulumi resource."""
        raise NotImplementedError
