"""Order lifecycle and pricing services."""
from typing import List
from app.models.order import Order, OrderItem
from app.config import settings

class OrderService:
    def __init__(self):
        self._orders = {}
        self._counter = 1

    def calculate_total(self, items: List[OrderItem]) -> float:
        """Calculate total order price."""
        if len(items) > settings.MAX_ORDER_ITEMS:
            raise ValueError(f"Order exceeds maximum items limit ({settings.MAX_ORDER_ITEMS})")
        return round(sum(item.quantity * item.unit_price for item in items), 2)

    def create_order(self, user_id: int, items: List[OrderItem]) -> Order:
        """Create and store a new order."""
        if not items:
            raise ValueError("Order must have at least one item")
        total = self.calculate_total(items)
        order = Order(
            id=self._counter,
            user_id=user_id,
            items=items,
            total_amount=total,
            status="pending"
        )
        self._orders[order.id] = order
        self._counter += 1
        return order

    def get_order(self, order_id: int) -> Order:
        order = self._orders.get(order_id)
        if not order:
            raise KeyError(f"Order {order_id} not found")
        return order

    def update_status(self, order_id: int, new_status: str) -> Order:
        order = self.get_order(order_id)
        valid_statuses = ["pending", "paid", "shipped", "cancelled"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status {new_status}")
        order.status = new_status
        return order

order_service = OrderService()
