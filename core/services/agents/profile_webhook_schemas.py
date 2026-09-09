"""Pydantic shapes shared by the profile-webhook service and router.

Pure Pydantic v2 — no FastAPI imports — so the service can validate the same
shapes the router accepts without coupling to the transport.
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class RequestIdentifierIn(BaseModel):
    """One identifier mapping: which known caller field to send, under what
    param name, and where (query string vs JSON body).

    v1 supports only ``phone``; the list shape lets ``email``/``name`` be added
    later without a schema migration.
    """

    model_config = ConfigDict(populate_by_name=True)

    identifier: Literal["phone"]
    param: str = Field(min_length=1, max_length=120)
    # "path" substitutes the value into a ``{param}`` placeholder in the URL.
    in_: Literal["query", "body", "path"] = Field(alias="in")


# Validate each resolved response value is a usable scalar before it is injected
# into the prompt. A dict/list/None fails → that variable falls back to its
# default ``value`` (handled by the fill-only-empty merge in the runner).
ScalarAdapter: TypeAdapter = TypeAdapter(Union[str, int, float, bool])


def is_usable_scalar(value: object) -> bool:
    """True when ``value`` coerces to a prompt-injectable scalar (str/int/float/
    bool) and is not a bool-as-None edge. ``None``/dict/list → False."""
    if value is None or isinstance(value, (dict, list)):
        return False
    try:
        ScalarAdapter.validate_python(value)
    except Exception:  # noqa: BLE001 — validation failure = not usable
        return False
    return True
