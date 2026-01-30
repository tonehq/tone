from sqlalchemy import event
import time


def _set_updated_at(mapper, connection, target):
    if hasattr(target, "updated_at"):
        target.updated_at = int(time.time())


def setup_timestamp_listeners(base):
    event.listen(base, "before_update", _set_updated_at, propagate=True)
