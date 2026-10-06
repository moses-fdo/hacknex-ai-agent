from typing import List, Optional, Dict
from app.models.order import Order, OrderItem
from app.auth.permissions import can_access_order

class OrderService:
    def __init__(self):
        self._orders: Dict[str, Order] = {}

    def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
        if not items:
            raise ValueError("An order must contain at least one item")
        total = sum(item.quantity * item.price for item in items)
        order_id = f"ord_{len(self._orders) + 1:04d}"
        order = Order(
            order_id=order_id,
            user_id=user_id,
            items=items,
            total_amount=round(total, 2),
            status="confirmed"
        )
        self._orders[order_id] = order
        return order

    def get_order(self, order_id: str, requesting_user_id: str, roles: List[str]) -> Optional[Order]:
        order = self._orders.get(order_id)
        if not order:
            return None
        if not can_access_order(requesting_user_id, order.user_id, roles):
            raise PermissionError("Access denied to order")
        return order

    def cancel_order(self, order_id: str, requesting_user_id: str, roles: List[str]) -> bool:
        order = self.get_order(order_id, requesting_user_id, roles)
        if not order:
            return False
        if order.status == "cancelled":
            return False
        order.status = "cancelled"
        return True
