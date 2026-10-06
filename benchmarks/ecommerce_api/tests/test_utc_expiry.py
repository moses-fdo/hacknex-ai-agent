import pytest
from datetime import datetime, timezone, timedelta
from app.auth.tokens import is_token_expired, create_access_token, verify_token

def test_token_expiration_utc_alignment():
    # A token expiring 30 seconds into the future UTC must NOT be expired
    now_utc = datetime.now(timezone.utc)
    future_ts = (now_utc + timedelta(seconds=30)).timestamp()
    assert is_token_expired(future_ts) is False

def test_end_to_end_utc_token_verification():
    token = create_access_token({'sub': 'test_utc_user'}, expires_delta=timedelta(minutes=15))
    payload = verify_token(token)
    assert payload is not None
    assert payload['sub'] == 'test_utc_user'
