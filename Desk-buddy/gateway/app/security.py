import hashlib
import hmac
import secrets
from .config import settings

def make_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def hash_otp(challenge_id: str, otp: str) -> str:
    return hashlib.sha256(f"{challenge_id}:{otp}:{settings.device_token_pepper}".encode()).hexdigest()

def make_device_token() -> str:
    return "dbd_" + secrets.token_urlsafe(32)

def make_session_token() -> str:
    return "dbs_" + secrets.token_urlsafe(32)

def hash_device_token(token: str) -> str:
    return hashlib.sha256(f"device:{token}:{settings.device_token_pepper}".encode()).hexdigest()

def hash_session_token(token: str) -> str:
    return hashlib.sha256(f"session:{token}:{settings.device_token_pepper}".encode()).hexdigest()

def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

def security_secret_configured() -> bool:
    return len(settings.device_token_pepper) >= 32 and settings.device_token_pepper != "replace-with-a-long-random-secret"
