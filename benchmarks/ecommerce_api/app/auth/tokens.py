"""Token generation, signature verification, and expiration check.

NOTE: Contains the planted timezone defect in is_token_expired() as specified in PRD v1.3.
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import settings

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data + padding)

def generate_token(payload: Dict[str, Any], expires_in: Optional[int] = None) -> str:
    """Generate a signed HMAC-SHA256 token with UTC expiration timestamp."""
    lifetime = expires_in if expires_in is not None else settings.TOKEN_LIFETIME_SECONDS
    # The expiration is generated properly as an aware UTC timestamp:
    exp = int(datetime.now(timezone.utc).timestamp()) + lifetime
    
    header = {"alg": "HS256", "typ": "JWT"}
    full_payload = {**payload, "exp": exp}
    
    encoded_header = _base64url_encode(json.dumps(header).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(full_payload).encode("utf-8"))
    
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)
    
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def verify_token_signature(token: str) -> Optional[Dict[str, Any]]:
    """Verify HMAC signature and return payload dict if valid."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    encoded_header, encoded_payload, encoded_sig = parts
    
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _base64url_decode(encoded_sig)
    
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None
        
    try:
        payload = json.loads(_base64url_decode(encoded_payload).decode("utf-8"))
        return payload
    except Exception:
        return None

def is_token_expired(payload: Dict[str, Any]) -> bool:
    """Check if token is expired.
    
    DEFECT: datetime.utcnow().timestamp() returns a timestamp treating naive UTC
    as local system time in POSIX platforms. When running in a non-UTC timezone (e.g. Asia/Kolkata),
    this produces an offset error equal to the UTC offset!
    """
    exp = payload.get("exp")
    if exp is None:
        return True
    
    # PLANTED DEFECT: Naive utcnow converted to timestamp
    current_time = datetime.utcnow().timestamp()
    return current_time >= exp

def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate signature and check expiration."""
    payload = verify_token_signature(token)
    if not payload:
        return None
    if is_token_expired(payload):
        return None
    return payload
