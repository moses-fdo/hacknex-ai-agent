import pytest
from app.auth.permissions import has_permission, can_access_order

def test_admin_has_full_permissions():
    roles = ["admin"]
    assert has_permission(roles, "read") is True
    assert has_permission(roles, "write") is True
    assert has_permission(roles, "delete") is True
    assert has_permission(roles, "manage_users") is True

def test_customer_has_limited_permissions():
    roles = ["customer"]
    assert has_permission(roles, "read") is True
    assert has_permission(roles, "create_order") is True
    assert has_permission(roles, "delete") is False
    assert has_permission(roles, "manage_users") is False

def test_manager_has_order_permissions():
    roles = ["manager"]
    assert has_permission(roles, "manage_orders") is True
    assert has_permission(roles, "manage_users") is False

def test_unrecognized_role_has_no_permissions():
    assert has_permission(["guest"], "read") is False
    assert has_permission([], "read") is False

def test_admin_can_access_any_order():
    assert can_access_order("admin_user", "customer_owner", ["admin"]) is True

def test_manager_can_access_any_order():
    assert can_access_order("mgr_user", "customer_owner", ["manager"]) is True

def test_customer_can_access_own_order():
    assert can_access_order("cust_1", "cust_1", ["customer"]) is True

def test_customer_cannot_access_foreign_order():
    assert can_access_order("cust_1", "cust_2", ["customer"]) is False
