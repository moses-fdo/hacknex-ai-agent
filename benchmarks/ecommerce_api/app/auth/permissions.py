from typing import List, Dict, Any

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": ["read", "write", "delete", "manage_users"],
    "manager": ["read", "write", "manage_orders"],
    "customer": ["read", "create_order"],
}

def has_permission(roles: List[str], required_permission: str) -> bool:
    """Verifies whether any role assigned to the subject possesses the required permission."""
    for role in roles:
        permissions = ROLE_PERMISSIONS.get(role, [])
        if required_permission in permissions:
            return True
    return False

def can_access_order(user_id: str, order_user_id: str, roles: List[str]) -> bool:
    """Customers can only access their own orders; admin/manager can access any."""
    if "admin" in roles or "manager" in roles:
        return True
    return user_id == order_user_id
