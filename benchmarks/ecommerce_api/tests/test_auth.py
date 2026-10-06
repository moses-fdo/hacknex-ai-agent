import pytest
import time
from datetime import timedelta
from app.auth.tokens import create_access_token, verify_token, generate_signature

def test_create_and_verify_valid_token():
    payload = {"sub": "user_123", "role": "customer"}
    token = create_access_token(payload)
    assert token is not None
    decoded = verify_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_123"
    assert decoded["role"] == "customer"
    assert "exp" in decoded

def test_tampered_token_signature_fails():
    token = create_access_token({"sub": "user_123"})
    parts = token.split(".")
    tampered_payload = parts[1] + "tamper"
    tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
    assert verify_token(tampered_token) is None

def test_malformed_token_returns_none():
    assert verify_token("not-a-valid-token") is None
    assert verify_token("a.b") is None
    assert verify_token("") is None

def test_token_with_custom_expiration():
    delta = timedelta(hours=2)
    token = create_access_token({"sub": "user_456"}, expires_delta=delta)
    decoded = verify_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_456"

def test_expired_token_is_rejected():
    token = create_access_token({"sub": "user_789"}, expires_delta=timedelta(seconds=-10))
    decoded = verify_token(token)
    assert decoded is None

def test_signature_stability():
    sig1 = generate_signature("header", "payload")
    sig2 = generate_signature("header", "payload")
    assert sig1 == sig2
    assert len(sig1) > 10

def test_token_contains_issued_at():
    token = create_access_token({"sub": "user_iat"})
    decoded = verify_token(token)
    assert decoded is not None
    assert "iat" in decoded
    assert decoded["iat"] <= time.time() + 5

def test_token_preserves_arbitrary_metadata():
    meta = {"sub": "u_meta", "team": "dev", "flags": [1, 2, 3]}
    token = create_access_token(meta)
    decoded = verify_token(token)
    assert decoded is not None
    assert decoded["team"] == "dev"
    assert decoded["flags"] == [1, 2, 3]
