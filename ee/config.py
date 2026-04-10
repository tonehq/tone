from shared.config import settings


class EESettings:
    """EE settings that extends shared settings with multi-tenant flag."""

    def __init__(self, base_settings):
        self._base = base_settings
        self.IS_MULTI_TENANT: bool = True

    def __getattr__(self, name):
        return getattr(self._base, name)


ee_settings = EESettings(settings)
