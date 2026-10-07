"""Auth and token tests (8 tests)."""
import time
from app.auth.tokens import generate_token, verify_token_signature, is_token_expired, validate_token

def test_generate_token_structure():
    token = generate_token({"sub": "user1"})
    assert token.count(".") == 2

def test_verify_valid_token():
    token = generate_token({"sub": "user123", "role": "admin"})
    payload = verify_token_signature(token)
    assert payload is not None
    assert payload["sub"] == "user123"

def test_tampered_token_signature_fails():
    token = generate_token({"sub": "user123"})
    tampered = token[:-4] + "abcd"
    assert verify_token_signature(tampered) is None

def test_malformed_token_fails():
    assert verify_token_signature("not.a.valid.jwt.token") is None

def test_token_contains_exp_claim():
    token = generate_token({"sub": "user456"})
    payload = verify_token_signature(token)
    assert "exp" in payload
    assert isinstance(payload["exp"], int)

def test_token_explicit_lifetime():
    token = generate_token({"sub": "user456"}, expires_in=100)
    payload = verify_token_signature(token)
    assert payload["exp"] > time.time()

def test_expired_token_marked_expired():
    # Past expiration (24 hours ago)
    payload = {"sub": "old_user", "exp": int(time.time()) - 86400}
    assert is_token_expired(payload) is True

def test_validate_token_success():
    token = generate_token({"sub": "testuser", "roles": ["customer"]})
    validated = validate_token(token)
    assert validated is not None
    assert validated["sub"] == "testuser"
