"""Single source of truth for OAuth 2.1 PKCE (RFC 7636) primitives.

PKCE is used by both the catalog OAuth flow (``core/api/v1/oauth.py``) and the
generic MCP discovery flow (``core/services/mcp_oauth_service.py``). Keeping
the verifier-generation logic here avoids two copies drifting out of sync.
"""

import base64
import hashlib
import secrets
from typing import Tuple


def pkce_pair() -> Tuple[str, str]:
    """Return a fresh ``(verifier, challenge)`` pair using the S256 method.

    The verifier is 384 random bits, base64url-encoded (no padding) — well
    inside the spec's 43–128 character window. The challenge is the
    SHA-256 of the verifier, also base64url-encoded with padding stripped.
    """
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    return verifier, challenge
