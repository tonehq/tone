"""TEMPORARY test aid for the profile-variable webhook data source.

A public, unauthenticated MOCK lookup endpoint that returns SYNTHETIC caller
data (no DB access, no real records) so you can point an agent's webhook at your
own deployed app and exercise every case. Safe to deploy; delete this file + its
two ``main.py`` registrations once testing is done.

Scenarios (via ``?scenario=``):
- ``success`` (default) — nested JSON: ``{"properties": {"name", ...}, "phone"}``
- ``list``    — a JSON array (tests "take the first item")
- ``flat``    — no ``properties`` wrapper (tests a path that won't resolve → fallback)
- ``notfound``— HTTP 404 (tests non-2xx → fallback)
- ``error``   — HTTP 500 (tests non-2xx → fallback)
- ``slow``    — sleeps 5s, past the 3s webhook cap (tests timeout → fallback)
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from loguru import logger

router = APIRouter()

_NAMES = ["John Doe", "Jane Smith", "Alex Kim", "Sam Patel", "Riya Nair"]
_TIERS = ["gold", "silver", "bronze"]


def _fake_record(phone: str) -> dict:
    """Deterministic synthetic 'customer' derived from the phone digits."""
    digits = "".join(c for c in (phone or "") if c.isdigit()) or "0"
    seed = int(digits[-4:] or "0")
    name = _NAMES[seed % len(_NAMES)]
    first = name.split()[0]
    return {
        "properties": {
            "name": name,
            "first_name": first,
            "email": f"{first.lower()}@example.com",
            "tier": _TIERS[seed % len(_TIERS)],
        },
        "phone": phone,
    }


async def _build(phone: str, scenario: str) -> JSONResponse:
    if scenario == "error":
        return JSONResponse(status_code=500, content={"error": "simulated server error"})
    if scenario == "notfound":
        return JSONResponse(status_code=404, content={"error": "no customer for this phone"})
    if scenario == "slow":
        await asyncio.sleep(5)  # exceeds the 3s webhook cap → variables fall back
        return JSONResponse(content=_fake_record(phone))
    if scenario == "list":
        return JSONResponse(content=[_fake_record(phone), _fake_record(phone + "9")])
    if scenario == "flat":
        # No ``properties`` wrapper — a source_path of ``properties.name`` won't
        # resolve, so that variable falls back to its default value.
        rec = dict(_fake_record(phone)["properties"])
        rec["phone"] = phone
        return JSONResponse(content=rec)
    return JSONResponse(content=_fake_record(phone))


async def _phone_from_request(request: Request) -> str:
    """Read the phone from a POST body (``phone`` or ``caller_number``); empty
    / non-JSON bodies are fine for a mock."""
    body: dict = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 — empty / non-JSON body is fine for a mock
        logger.debug("[webhook-test] no JSON body on POST")
    return str(body.get("phone") or body.get("caller_number") or "")


@router.get("/webhook-test/lookup")
async def webhook_test_lookup_get(
    phone: str = Query(default=""),
    scenario: str = Query(default="success"),
):
    return await _build(phone, scenario)


@router.post("/webhook-test/lookup")
async def webhook_test_lookup_post(
    request: Request,
    scenario: str = Query(default="success"),
):
    return await _build(await _phone_from_request(request), scenario)


# ── Path-based scenario (robust) ──────────────────────────────────────────
# The scenario lives in the URL PATH (…/lookup/notfound) instead of a query
# string, so it survives regardless of how the webhook config stores the URL —
# no query params to lose. Prefer these for testing.


@router.get("/webhook-test/lookup/{scenario}")
async def webhook_test_lookup_get_path(scenario: str, phone: str = Query(default="")):
    return await _build(phone, scenario)


@router.post("/webhook-test/lookup/{scenario}")
async def webhook_test_lookup_post_path(scenario: str, request: Request):
    return await _build(await _phone_from_request(request), scenario)


# ── Match-my-number (realistic real-call test) ────────────────────────────
# Returns a record ONLY when the incoming phone matches ``allowed`` (put YOUR
# number in the URL path, e.g. …/webhook-test/match/18637658026); every other
# caller gets 404 so the variable falls back to its default. Lets you place a
# real inbound call from your phone and see it resolve, while other numbers
# exercise the fallback. Comparison is on the last 10 digits, so +country-code
# / formatting differences don't matter.


def _digits(p: str) -> str:
    return "".join(c for c in (p or "") if c.isdigit())[-10:]


def _match_response(allowed: str, phone: str) -> JSONResponse:
    if phone and _digits(phone) and _digits(phone) == _digits(allowed):
        return JSONResponse(content=_fake_record(phone))
    return JSONResponse(status_code=404, content={"error": "no customer for this phone"})


@router.get("/webhook-test/match/{allowed}")
async def webhook_test_match_get(allowed: str, phone: str = Query(default="")):
    return _match_response(allowed, phone)


@router.post("/webhook-test/match/{allowed}")
async def webhook_test_match_post(allowed: str, request: Request):
    return _match_response(allowed, await _phone_from_request(request))


# ── Phone-in-the-path (tests the "URL path" identifier location) ──────────
# Configure the webhook URL as …/webhook-test/by-path/{phone} with the phone
# identifier set to location "URL path"; the caller's number is substituted
# into the path. Returns a record for any non-empty phone, else 404.


@router.get("/webhook-test/by-path/{phone}")
async def webhook_test_by_path(phone: str):
    if not _digits(phone):
        return JSONResponse(status_code=404, content={"error": "no phone in path"})
    return JSONResponse(content=_fake_record(phone))
