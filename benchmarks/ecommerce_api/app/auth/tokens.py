import base64
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from app.config import settings

def generate_signature(header_b64: str, payload_b64: str) -> str:
    """Simulated HMAC signature for testing without external crypto dependencies."""
    combined = f"{header_b64}.{payload_b64}.{settings.SECRET_KEY}"
    return base64.urlsafe_b64encode(combined.encode()).decode().rstrip("=")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed bearer token with expiration."""
    header = {"alg": settings.ALGORITHM, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    
    payload = data.copy()
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    
    payload["exp"] = expire.timestamp()
    payload["iat"] = now_utc.timestamp()
    
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = generate_signature(header_b64, payload_b64)
    return f"{header_b64}.{payload_b64}.{signature}"

def is_token_expired(expires_at: float) -> bool:
    """
    Checks if expiration timestamp has passed against UTC epoch.
    Fixed: Uses timezone-aware UTC datetime for consistent evaluation across environments.
    """
    now_ts = datetime.now(timezone.utc).timestamp()
    return now_ts >= expires_at

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and verifies a token signature and validity."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature = parts
        expected_sig = generate_signature(header_b64, payload_b64)
        if signature != expected_sig:
            return None
        
        # Decode payload
        rem = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
        payload_json = base64.urlsafe_b64decode(padded.encode()).decode()
        payload = json.loads(payload_json)
        
        exp = payload.get("exp")
        if exp is not None and is_token_expired(exp):
            return None
            
        return payload
    except Exception:
        return None
