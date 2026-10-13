from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://rpa:rpa_secret@localhost:5432/research_proto"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev-secret-change-in-prod-32chars"
    OPENAI_API_KEY: str = ""
    DEFAULT_MODEL: str = "gpt-4o-mini"
    STORAGE_PATH: str = "/tmp/rpa-artifacts"
    SANDBOX_TIMEOUT_SEC: int = 120
    MAX_PAPER_CHARS: int = 40000

    class Config:
        env_file = ".env"

settings = Settings()
