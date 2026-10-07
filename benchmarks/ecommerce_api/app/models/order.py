"""Order and Line Item models."""
from typing import List
from pydantic import BaseModel, Field

class OrderItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0.0)

class Order(BaseModel):
    id: int
    user_id: int
    items: List[OrderItem]
    total_amount: float
    status: str = "pending"  # pending, paid, shipped, cancelled
