from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./housedreamer.db"
    crawler_delay: float = 2.0
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
