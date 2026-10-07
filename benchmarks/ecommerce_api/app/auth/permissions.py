"""Role-based access control and permission enforcement."""
from typing import Dict, List, Any

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": ["order:read", "order:write", "order:delete", "user:read", "user:write"],
    "manager": ["order:read", "order:write", "user:read"],
    "customer": ["order:read", "order:write"],
}

def has_permission(roles: List[str], required_permission: str) -> bool:
    """Check if any of the given roles grants the required permission."""
    for role in roles:
        permissions = ROLE_PERMISSIONS.get(role, [])
        if required_permission in permissions:
            return True
    return False

def check_user_access(user_payload: Dict[str, Any], required_permission: str) -> bool:
    """Check if a decoded user token payload has access."""
    roles = user_payload.get("roles", [])
    if not isinstance(roles, list):
        return False
    return has_permission(roles, required_permission)
