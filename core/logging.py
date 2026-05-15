import sys
import uuid

from loguru import logger


def setup_logging():
    """Configure loguru with trace_id support. Call once at app startup."""
    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | "
            "trace_id={extra[trace_id]} | {message}"
        ),
        level="DEBUG",
    )
    logger.configure(extra={"trace_id": "none"})


def make_trace_id(agent_id, call_log_id=0):
    """Generate trace ID in format: {uuid_short}-{agent_id}-{call_log_id}."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"{short_uuid}-{agent_id}-{call_log_id}"


def update_trace_id_with_call_log(current_trace_id, call_log_id):
    """Replace the trailing call_log_id placeholder with the real value."""
    parts = current_trace_id.rsplit("-", 1)
    return f"{parts[0]}-{call_log_id}"
