import base64
import json
import logging
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = settings.JWT_SECRET_KEY.encode()
    salt = b'tone_salt'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    derived_key = base64.urlsafe_b64encode(kdf.derive(key))
    return Fernet(derived_key)


def encrypt(data: str) -> str:
    fernet = _get_fernet()
    encrypted = fernet.encrypt(data.encode())
    return encrypted.decode()


def decrypt(encrypted_data: str) -> str:
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_data.encode())
    return decrypted.decode()


def encrypt_json(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Encrypt a dict for storage in a JSONB column.

    Returns a wrapper dict ``{"data": "<fernet-encrypted-json>"}`` so the
    column itself stays valid JSONB while the sensitive payload is opaque.
    """
    if not payload:
        return {"data": None}
    return {"data": encrypt(json.dumps(payload))}


def decrypt_json(stored: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Inverse of ``encrypt_json``. Returns ``{}`` for empty input.

    Decryption / JSON failures are re-raised — silently returning ``{}`` here
    masks a rotated key or corrupted ciphertext and lets reconnect flows
    overwrite a credentials blob with empty values (losing the previous
    refresh token). Operators should see the failure.
    """
    if not stored or not isinstance(stored, dict):
        return {}
    blob = stored.get("data")
    if not blob:
        return {}
    try:
        return json.loads(decrypt(blob))
    except Exception:
        logger.exception("Failed to decrypt stored credentials blob")
        raise
