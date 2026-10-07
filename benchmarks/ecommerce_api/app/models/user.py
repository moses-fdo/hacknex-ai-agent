"""User models and role allocations."""
from typing import List, Optional
from pydantic import BaseModel, EmailStr

class User(BaseModel):
    id: int
    username: str
    email: str
    roles: List[str] = ["customer"]
    is_active: bool = True

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    roles: Optional[List[str]] = None
