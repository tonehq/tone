"""Business-only email guard shared by every signup / invite entrypoint.

Two lists are combined:
* ``PERSONAL_EMAIL_DOMAINS`` — hand-curated free-mail providers
  (gmail/yahoo/outlook/…). Consumer providers are *not* considered disposable
  by upstream lists, so we own this set.
* ``disposable_email_domains.blocklist`` — ~4k throwaway/temp providers,
  auto-updated by the community package.

Callers use :func:`assert_business_email` (HTTP-shaped 400) at API/service
boundaries; use :func:`is_personal_email` for silent checks.
"""

from __future__ import annotations

from typing import Final

from disposable_email_domains import blocklist as _DISPOSABLE_BLOCKLIST
from fastapi import HTTPException, status


# Free-mail providers we deliberately block for B2B signups. Kept small and
# hand-curated — expanding this list is a business decision, not a maintenance
# task. All entries are lowercase.
PERSONAL_EMAIL_DOMAINS: Final[frozenset[str]] = frozenset(
    {
        # Google
        "gmail.com",
        "googlemail.com",
        # Yahoo
        "yahoo.com",
        "yahoo.co.in",
        "yahoo.co.uk",
        "ymail.com",
        "rocketmail.com",
        # Microsoft
        "outlook.com",
        "outlook.in",
        "hotmail.com",
        "hotmail.co.uk",
        "live.com",
        "msn.com",
        # Apple
        "icloud.com",
        "me.com",
        "mac.com",
        # Other consumer providers
        "aol.com",
        "proton.me",
        "protonmail.com",
        "pm.me",
        "gmx.com",
        "gmx.net",
        "gmx.de",
        "mail.com",
        "yandex.com",
        "yandex.ru",
        "tutanota.com",
        "tuta.io",
        "fastmail.com",
        "zoho.com",
        # Regional consumer providers
        "qq.com",
        "163.com",
        "126.com",
        "sina.com",
        "rediffmail.com",
    }
)


PERSONAL_EMAIL_ERROR: Final[str] = (
    "Please use your company email address. Personal email addresses "
    "(Gmail, Yahoo, Outlook, etc.) aren't allowed."
)


def _extract_domain(email: str) -> str:
    """Return the lowercase domain portion of ``email``, or ``""`` if malformed.

    Format validation itself is left to Pydantic ``EmailStr`` / the frontend
    Zod ``.email()`` check — this helper only cares about the domain lookup.
    """
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].strip().lower()


def is_personal_email(email: str) -> bool:
    """True when the email's domain is a consumer or disposable provider."""
    domain = _extract_domain(email)
    if not domain:
        return False
    if domain in PERSONAL_EMAIL_DOMAINS:
        return True
    return domain in _DISPOSABLE_BLOCKLIST


def assert_business_email(email: str) -> None:
    """Raise ``HTTP 400`` when ``email`` isn't a business address.

    Callers: ``AuthService.signup_v2``, ``AuthService.invite_user_to_organization``,
    and any future signup/invite entrypoint. Existing users must NOT be
    re-checked (login, password reset, sign-in code) — the guard is for new
    identities only.
    """
    if is_personal_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PERSONAL_EMAIL_ERROR,
        )
