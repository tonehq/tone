"""In-call idempotency for create-type tool calls.

Voice agents can fire the same booking tool twice within one call. The common
cause: the caller barges in (starts speaking) at the exact moment a tool batch
is completing — the turn is interrupted, so the tool's result is discarded
("FunctionCallResultFrame tool_call_id ... is not running"). The LLM, never
having seen the success, re-issues the booking after the caller re-confirms.
Because the booking tools (``clickup_create_task``, calendar ``create_event``)
always create a NEW record, that retry produces a duplicate ClickUp task /
calendar event — and the first calendar event was already committed before the
interruption, so it can't be undone.

To stop this we dedupe create-type tool calls within a single call by an
*identity* derived from the tool + record name/title + the concrete dates/times
involved. The dates/times are the safety mechanism: a retry of the SAME booking
shares them (so it's suppressed even if prose like the room type was reworded),
while two GENUINELY DIFFERENT bookings for the same guest differ on date/time
(so they are NEVER collapsed and no booking is lost).

We deliberately require BOTH a name AND at least one date/time before deduping.
If we can't find a strong identity, we return ``None`` (do NOT dedupe) — erring
toward an occasional duplicate rather than ever dropping real booking data.
"""

import re
from typing import Optional

_CREATE_HINT = "create"

# Dates like 2026-07-05 and times like 18:00 / 9:30. These appear both in
# structured args (calendar date/start_time) and free text (ClickUp's
# description, e.g. "Check-in Date: 2026-07-05, Check-out Date: 2026-07-12").
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")


def _scan_temporal(args: dict) -> tuple:
    """Return (sorted unique dates, sorted unique times) found anywhere in args."""
    dates, times = set(), set()
    for value in args.values():
        if value is None:
            continue
        text = value if isinstance(value, str) else str(value)
        dates.update(_DATE_RE.findall(text))
        times.update(_TIME_RE.findall(text))
    return tuple(sorted(dates)), tuple(sorted(times))


def booking_signature(tool_name: str, args, is_create: Optional[bool] = None) -> Optional[str]:
    """Return a per-call idempotency key for a create-type tool call.

    Returns ``None`` when the call should NOT be deduped — i.e. it isn't a create
    operation, args aren't a dict, no stable record name is present, or no
    date/time identity can be found (in which case we prefer allowing the call
    over risking a collapse of two distinct bookings).

    Args:
        tool_name: The tool/function name (e.g. ``clickup_create_task``).
        args: The arguments dict passed to the tool.
        is_create: Force create-detection. When ``None`` (default), inferred from
            the presence of "create" in ``tool_name``. Pass ``True`` for tools
            whose create-ness lives in an arg instead (e.g. the calendar tool's
            ``action == "create_event"``).
    """
    if is_create is None:
        is_create = bool(tool_name) and _CREATE_HINT in tool_name.lower()
    if not is_create or not isinstance(args, dict):
        return None

    name = args.get("name") or args.get("title") or args.get("summary")
    if not name:
        return None

    dates, times = _scan_temporal(args)
    # Require a temporal anchor so we never dedupe on name alone — that's what
    # protects two same-guest, different-date bookings from being collapsed.
    if not dates and not times:
        return None

    scope = args.get("list_id") or args.get("calendar_id") or ""
    # A stable per-booking party identifier (attendee email / phone). Folding it in
    # keeps two distinct same-title, same-date bookings apart even when there's no
    # time to tell them apart (e.g. two all-day reservations in one call). We use
    # only structured identity fields — never free-text prose — so a genuine retry
    # of the SAME booking still shares it and is suppressed.
    party = args.get("attendee_email") or args.get("email") or args.get("phone") or ""
    return "|".join([
        str(tool_name).lower(),
        str(scope),
        str(name).strip().lower(),
        str(party).strip().lower(),
        ",".join(dates),
        ",".join(times),
    ])


def is_cacheable_result(result) -> bool:
    """Whether a create-tool result should be cached for in-call idempotency.

    A failed create returns a result rather than raising (e.g. the calendar tool's
    ``"Failed to create event: ..."`` or an MCP server's error payload). Caching it
    would replay that failure on a same-signature retry and permanently drop a
    booking that might have succeeded — the opposite of this module's goal. So we
    refuse to cache results that look like an error/failure. Non-string results
    (the success payloads of some create tools) are treated as cacheable.
    """
    if isinstance(result, str):
        return not result.strip().lower().startswith(("error", "failed"))
    return True
