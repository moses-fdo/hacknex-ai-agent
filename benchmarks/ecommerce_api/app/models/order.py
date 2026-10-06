from pydantic import BaseModel, Field
from typing import List

class OrderItem(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)
    price: float = Field(gt=0.0)

class Order(BaseModel):
    order_id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    status: str = "pending"
