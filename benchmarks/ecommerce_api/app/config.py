"""Configuration settings for Ecommerce API."""
from dataclasses import dataclass

@dataclass
class Settings:
    PROJECT_NAME: str = "Ecommerce API"
    SECRET_KEY: str = "super-secret-aether-benchmark-key-2026"
    TOKEN_LIFETIME_SECONDS: int = 3600  # 1 hour
    DEFAULT_CURRENCY: str = "USD"
    MAX_ORDER_ITEMS: int = 50

settings = Settings()
