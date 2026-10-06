class Settings:
    PROJECT_NAME: str = "Aether Commerce API"
    VERSION: str = "2.1.0"
    SECRET_KEY: str = "super-secret-production-key-9988"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60

settings = Settings()
