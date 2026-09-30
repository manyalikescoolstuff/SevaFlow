from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "SevaFlow Backend"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sevaflow"
    HARDWARE_SECRET: str = "change_me_in_production"
    # JWT for staff auth (simple shared secret for V1)
    STAFF_JWT_SECRET: str = "sevaflow_staff_jwt_secret_change_in_prod"
    STAFF_JWT_ALGORITHM: str = "HS256"
    STAFF_JWT_EXPIRE_MINUTES: int = 480  # 8 hours
    ENABLE_DEMO_MODE: bool = True  # Enable for testing

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
