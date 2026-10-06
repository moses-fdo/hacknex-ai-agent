import pytest
from app.models.order import OrderItem
from app.services.order_service import OrderService

def test_order_creation_success():
    service = OrderService()
    items = [
        OrderItem(item_id="item_1", quantity=2, price=25.0),
        OrderItem(item_id="item_2", quantity=1, price=50.0)
    ]
    order = service.create_order("user_100", items)
    assert order.order_id == "ord_0001"
    assert order.total_amount == 100.0
    assert order.status == "confirmed"

def test_order_creation_empty_items_fails():
    service = OrderService()
    with pytest.raises(ValueError):
        service.create_order("user_100", [])

def test_get_order_owner_access():
    service = OrderService()
    items = [OrderItem(item_id="i1", quantity=1, price=10.0)]
    created = service.create_order("user_100", items)
    fetched = service.get_order(created.order_id, "user_100", ["customer"])
    assert fetched is not None
    assert fetched.order_id == created.order_id

def test_get_order_non_owner_denied():
    service = OrderService()
    items = [OrderItem(item_id="i1", quantity=1, price=10.0)]
    created = service.create_order("user_100", items)
    with pytest.raises(PermissionError):
        service.get_order(created.order_id, "attacker_999", ["customer"])

def test_admin_can_fetch_any_order():
    service = OrderService()
    items = [OrderItem(item_id="i1", quantity=1, price=10.0)]
    created = service.create_order("user_100", items)
    fetched = service.get_order(created.order_id, "admin_user", ["admin"])
    assert fetched is not None

def test_cancel_order_success():
    service = OrderService()
    items = [OrderItem(item_id="i1", quantity=1, price=10.0)]
    created = service.create_order("user_100", items)
    success = service.cancel_order(created.order_id, "user_100", ["customer"])
    assert success is True
    assert created.status == "cancelled"

def test_cancel_already_cancelled_order_returns_false():
    service = OrderService()
    items = [OrderItem(item_id="i1", quantity=1, price=10.0)]
    created = service.create_order("user_100", items)
    service.cancel_order(created.order_id, "user_100", ["customer"])
    assert service.cancel_order(created.order_id, "user_100", ["customer"]) is False

def test_get_non_existent_order_returns_none():
    service = OrderService()
    assert service.get_order("ord_9999", "admin", ["admin"]) is None
