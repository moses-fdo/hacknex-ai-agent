"""Order lifecycle tests (8 tests)."""
import pytest
from app.models.order import OrderItem
from app.services.order_service import order_service

def test_calculate_total_single_item():
    items = [OrderItem(product_id=1, product_name="Widget", quantity=2, unit_price=10.5)]
    assert order_service.calculate_total(items) == 21.0

def test_calculate_total_multiple_items():
    items = [
        OrderItem(product_id=1, product_name="Widget", quantity=1, unit_price=10.0),
        OrderItem(product_id=2, product_name="Gadget", quantity=3, unit_price=5.25),
    ]
    assert order_service.calculate_total(items) == 25.75

def test_create_order_success():
    items = [OrderItem(product_id=1, product_name="Widget", quantity=1, unit_price=15.0)]
    order = order_service.create_order(user_id=42, items=items)
    assert order.id > 0
    assert order.user_id == 42
    assert order.status == "pending"
    assert order.total_amount == 15.0

def test_create_order_empty_items_raises():
    with pytest.raises(ValueError, match="at least one item"):
        order_service.create_order(user_id=1, items=[])

def test_get_order_existing():
    items = [OrderItem(product_id=9, product_name="Item", quantity=1, unit_price=5.0)]
    created = order_service.create_order(user_id=10, items=items)
    retrieved = order_service.get_order(created.id)
    assert retrieved.id == created.id

def test_get_order_nonexistent_raises():
    with pytest.raises(KeyError):
        order_service.get_order(999999)

def test_update_order_status_valid():
    items = [OrderItem(product_id=1, product_name="Item", quantity=1, unit_price=5.0)]
    order = order_service.create_order(user_id=1, items=items)
    updated = order_service.update_status(order.id, "paid")
    assert updated.status == "paid"

def test_update_order_status_invalid_raises():
    items = [OrderItem(product_id=1, product_name="Item", quantity=1, unit_price=5.0)]
    order = order_service.create_order(user_id=1, items=items)
    with pytest.raises(ValueError, match="Invalid status"):
        order_service.update_status(order.id, "destroyed")
