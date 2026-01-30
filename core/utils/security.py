import bcrypt
import secrets
import string
import hashlib


def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def generate_verification_code(length: int = 6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def generate_api_key() -> tuple[str, str, str]:
    key = secrets.token_urlsafe(32)
    key_prefix = key[:8]
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_prefix, key_hash


def verify_api_key(key: str, key_hash: str) -> bool:
    computed_hash = hashlib.sha256(key.encode()).hexdigest()
    return secrets.compare_digest(computed_hash, key_hash)
