import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.config import settings


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
