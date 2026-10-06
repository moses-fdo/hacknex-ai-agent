from pydantic import BaseModel
from typing import Optional, List

class User(BaseModel):
    id: str
    username: str
    email: str
    roles: List[str] = ["customer"]
    is_active: bool = True
