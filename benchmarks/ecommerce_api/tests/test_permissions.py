"""Role-based access tests (8 tests)."""
from app.auth.permissions import has_permission, check_user_access

def test_admin_has_order_read():
    assert has_permission(["admin"], "order:read") is True

def test_admin_has_order_delete():
    assert has_permission(["admin"], "order:delete") is True

def test_customer_lacks_order_delete():
    assert has_permission(["customer"], "order:delete") is False

def test_customer_has_order_write():
    assert has_permission(["customer"], "order:write") is True

def test_manager_has_user_read():
    assert has_permission(["manager"], "user:read") is True

def test_manager_lacks_order_delete():
    assert has_permission(["manager"], "order:delete") is False

def test_check_user_access_valid_payload():
    payload = {"sub": "u1", "roles": ["customer"]}
    assert check_user_access(payload, "order:read") is True

def test_check_user_access_invalid_payload():
    assert check_user_access({}, "order:read") is False
